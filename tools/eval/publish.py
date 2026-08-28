# -*- coding: utf-8 -*-
"""실행 결과를 상세 페이지의 표와 막대에 그대로 박는다.

손으로 옮겨 적으면 언젠가 어긋난다. 숫자는 실행 결과에서만 온다.
페이지 쪽에는 `data-m="키"` 만 달아 두면 여기서 채운다.

  <td data-m="tl.found.rate"><span class="tbd">—</span></td>
  <i data-m="tl.found.bar" style="width:0"></i>

사용
  python tools/eval/publish.py                 최신 실행 결과로 채운다
  python tools/eval/publish.py --dry           무엇이 바뀌는지만 본다
"""
import glob
import io
import json
import os
import re
import sys

import score as scoring   # 채점 로직을 그대로 쓴다. 두 벌로 나누면 값이 갈린다

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(HERE, 'runs')

# 어느 실행 파일이 어느 페이지로 가는가
TARGETS = [
    # TripLinker 는 평가셋이 넷이라 이름 앞을 정확히 잡아야 한다.
    # 'TripLinker*' 로 두면 가장 최근에 돌린 것 하나가 나머지 자리를 다 덮는다
    ('tl', 'TripLinker_경로*', 'projects/triplinker.html'),
    ('tlmt', 'TripLinker_멀티턴*', 'projects/triplinker.html'),
    ('tlq', 'TripLinker_쿼리*', 'projects/triplinker.html'),
    ('tlsafe', 'TripLinker_세이프티*', 'projects/triplinker.html'),
    ('cogi', 'COGI_카드*', 'projects/cogi.html'),   # 벤더 비교 실행과 섞이지 않게 좁힌다
    ('cogisafe', 'COGI_세이프티*', 'projects/cogi.html'),
    ('om', '오몽*', 'projects/omong.html'),
]


def latest(pattern):
    fs = glob.glob(os.path.join(RUNS, pattern + '.json'))
    fs = [f for f in fs if 'report' not in os.path.basename(f)]
    return sorted(fs, key=os.path.getmtime)[-1] if fs else None


def current_scorers(run):
    """실행 이름이 같은 실험 설정을 찾아 그 채점기를 쓴다. 없으면 실행에 저장된 것."""
    name = run.get('config', {}).get('name')
    for f in glob.glob(os.path.join(HERE, 'experiments', '*.json')):
        cfg = json.loads(io.open(f, encoding='utf-8').read())
        if cfg.get('name') == name and cfg.get('scorers'):
            return cfg['scorers']
    return None


def pct(n, d):
    return '—' if not d else '%.0f%%' % (100.0 * n / d)


def numbers(path):
    """실행 파일 하나에서 사이트에 실을 값을 뽑는다."""
    run = json.loads(io.open(path, encoding='utf-8').read())
    # 정답도 「지금 평가셋」을 따른다. 사이트에는 평가셋 정의서가 같이 실린다.
    # 문서에 적힌 정답과 옆에 적힌 점수가 다른 기준이면 둘 중 하나는 거짓말이 된다
    scoring.refresh_key(run)
    # 채점기는 실행 당시가 아니라 「지금 설정」을 따른다.
    # 같은 응답을 새 기준으로 다시 보는 게 실행과 채점을 나눈 이유다.
    table = scoring.grade(run, current_scorers(run))
    ms = table.pop('_latency', None)
    out = {'_n': len(run['results']), '_at': run.get('ran_at', '')}

    for name, v in table.items():
        key = re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')
        if v.get('values'):                      # dist — 분포
            tot = sum(v['values'].values())
            # 한 번도 안 나온 값도 0%로 적는다. 칸이 비면 안 잰 것처럼 읽힌다
            seen = dict(v['values'])
            for want in run['config'].get('dist_values', {}).get(name, []):
                seen.setdefault(want, 0)
            for val, cnt in seen.items():
                vk = re.sub(r'[^a-z0-9]+', '_', str(val).lower()).strip('_')
                out['%s.%s.rate' % (key, vk)] = pct(cnt, tot)
                out['%s.%s.bar' % (key, vk)] = '%.0f%%' % (100.0 * cnt / tot)
                out['%s.%s.n' % (key, vk)] = str(cnt)
        else:
            out[key + '.rate'] = pct(v['ok'], v['n'])
            out[key + '.bar'] = ('%.0f%%' % v['rate'])
            out[key + '.n'] = '%d/%d' % (v['ok'], v['n'])

    out['latency.median'] = ('%dms' % ms['median']) if ms else '—'
    out['latency.p90'] = ('%dms' % ms['p90']) if ms else '—'
    out['latency.sec'] = ('%.1f초' % (ms['median'] / 1000.0)) if ms else '—'
    out['set.n'] = '%d건' % out['_n']
    out['ran.at'] = _date(out['_at'])
    return out


def _date(stamp):
    return '%s.%s.%s' % (stamp[0:4], stamp[4:6], stamp[6:8]) if len(stamp) >= 8 else ''


def fill(html, prefix, vals):
    """`data-m="prefix.키"` 를 찾아 값을 넣는다. 막대는 width 로."""
    hit, miss = 0, []

    def one(m):
        nonlocal hit
        tag, attrs, key = m.group(1), m.group(2), m.group(3)
        if not key.startswith(prefix + '.'):
            return m.group(0)
        short = key[len(prefix) + 1:]
        if short not in vals:
            miss.append(short)
            return m.group(0)
        hit += 1
        v = vals[short]
        if short.endswith('.bar'):
            attrs2 = re.sub(r'style="[^"]*"', 'style="width:%s"' % v, attrs)
            if 'style=' not in attrs2:
                attrs2 += ' style="width:%s"' % v
            return '<%s%s></%s>' % (tag, attrs2, tag)
        return '<%s%s>%s</%s>' % (tag, attrs, v, tag)

    out = re.sub(r'<(\w+)([^>]*data-m="([^"]+)"[^>]*)>.*?</\1>', one, html, flags=re.S)
    return out, hit, miss


def main():
    dry = '--dry' in sys.argv
    for prefix, pattern, page in TARGETS:
        run = latest(pattern)
        p = os.path.join(SITE, page)
        if not run:
            print('  %-16s 실행 결과 없음 — 건너뜀' % prefix)
            continue
        vals = numbers(run)
        html = io.open(p, encoding='utf-8').read()
        out, hit, miss = fill(html, prefix, vals)
        print('  %-6s %-28s %2d칸 채움%s' %
              (prefix, os.path.basename(run)[:28], hit,
               ('  (값 없음: %s)' % ', '.join(sorted(set(miss))[:4])) if miss else ''))
        if not dry and out != html:
            io.open(p, 'w', encoding='utf-8', newline='').write(out)
    if dry:
        print('  --dry 라 파일은 안 건드렸다')
    return 0


if __name__ == '__main__':
    sys.exit(main())
