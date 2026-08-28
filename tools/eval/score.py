# -*- coding: utf-8 -*-
"""실행 결과를 채점해 사이트에 바로 붙는 표를 낸다.

사용
  python tools/eval/score.py tools/eval/runs/<파일>.json
  python tools/eval/score.py <실행1> <실행2>      전/후 비교표
"""
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scorers

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    return json.loads(io.open(p, encoding='utf-8').read())


def schemas():
    p = os.path.join(HERE, 'schemas.json')
    return load(p) if os.path.exists(p) else {}



def refresh_key(run):
    """정답 열만 지금의 평가셋에서 다시 읽는다.

    서비스에 보낸 입력(질문·코드 등)은 그대로다. 내가 채점 기준을 잘못 적어 둔 걸
    고쳤을 때, 그것 때문에 API 를 다시 쓰는 건 낭비다. 응답은 두고 정답만 갈아 끼운다.
    바뀌는 건 `expected_*` `expect_*` 로 시작하는 열뿐이다.
    """
    path = run['config'].get('set', '')
    if not os.path.isabs(path):
        path = os.path.join(HERE, path)
    if not os.path.exists(path):
        return 0
    with io.open(path, encoding='utf-8-sig', newline='') as fp:
        by_id = {r.get('id'): r for r in csv.DictReader(fp)}
    n = 0
    for r in run['results']:
        fresh = by_id.get(str(r.get('id')))
        if not fresh:
            continue
        for k, v in fresh.items():
            if (k.startswith('expected_') or k.startswith('expect_')) and r['row'].get(k) != v:
                r['row'][k] = v
                n += 1
    return n

def grade(run, override=None):
    """채점기별 통과율과 응답 시간 분포를 낸다.

    `override` 를 주면 실행할 때 저장된 채점기 대신 그걸 쓴다.
    같은 응답을 다른 기준으로 다시 보는 게 이 도구를 나눈 이유다.
    """
    sc = schemas()
    names = override or run['config'].get('scorers', [])
    res = run['results']
    table = {}
    for name in names:
        ok = skip = 0
        notes, values = [], {}
        for r in res:
            passed, note = scorers.run_one(name, r, sc)
            if name.startswith('dist:'):
                values[note] = values.get(note, 0) + 1
                skip += 1
                continue
            if passed is None:
                skip += 1
            elif passed:
                ok += 1
            elif len(notes) < 3 and note:
                notes.append('#%s %s' % (r['id'], note))
        counted = len(res) - skip
        rate = (ok * 100.0 / counted) if counted else 0.0
        table[name] = {'ok': ok, 'n': counted, 'skip': skip,
                       'rate': rate, 'notes': notes, 'values': values}
    ms = sorted(r['ms'] for r in res)
    table['_latency'] = {
        'median': ms[len(ms) // 2] if ms else 0,
        'p90': ms[int(len(ms) * .9) - 1] if ms else 0,
        'max': ms[-1] if ms else 0,
    }
    return table


def md_one(run, t):
    cfg = run['config']
    out = []
    out.append('### %s' % cfg.get('name', '(이름 없음)'))
    out.append('')
    out.append('- 평가셋 `%s` · %d건 실행 · %s' %
               (cfg.get('set', ''), len(run['results']), run.get('ran_at', '')))
    lat = t['_latency']
    out.append('- 응답 시간 중앙값 **%dms** · p90 %dms · 최대 %dms'
               % (lat['median'], lat['p90'], lat['max']))
    out.append('')
    out.append('| 항목 | 통과 | 전체 | 통과율 |')
    out.append('|---|---|---|---|')
    for name, v in t.items():
        if name.startswith('_') or v.get('values'):
            continue
        if v['n'] == 0:
            out.append('| %s | — | — | 건너뜀 (%d건) |' % (name, v['skip']))
        else:
            out.append('| %s | %d | %d | **%.1f%%** |' % (name, v['ok'], v['n'], v['rate']))
    out.append('')
    for name, v in t.items():
        if name.startswith('_') or not v.get('values'):
            continue
        total = sum(v['values'].values()) or 1
        out.append('%s 분포' % name)
        out.append('')
        out.append('| 값 | 건수 | 비율 |')
        out.append('|---|---|---|')
        for k, c in sorted(v['values'].items(), key=lambda x: -x[1]):
            out.append('| %s | %d | **%.1f%%** |' % (k, c, c * 100.0 / total))
        out.append('')
    fails = [(n, v) for n, v in t.items() if not n.startswith('_') and v['notes']]
    if fails:
        out.append('실패 예시')
        for n, v in fails:
            out.append('- `%s` — %s' % (n, ' / '.join(v['notes'])))
        out.append('')
    return '\n'.join(out)


def md_compare(a, ta, b, tb):
    out = []
    out.append('### 전 / 후 비교')
    out.append('')
    out.append('| 항목 | 개선 전 | 개선 후 | 차이 |')
    out.append('|---|---|---|---|')
    keys = [k for k in ta if not k.startswith('_')]
    for k in keys:
        if k not in tb:
            continue
        x, y = ta[k]['rate'], tb[k]['rate']
        out.append('| %s | %.1f%% | %.1f%% | %+.1f%%p |' % (k, x, y, y - x))
    la, lb = ta['_latency']['median'], tb['_latency']['median']
    out.append('| 응답 시간(중앙값) | %dms | %dms | %+dms |' % (la, lb, lb - la))
    out.append('')
    out.append('- 개선 전 `%s` (%d건)' % (a['config'].get('name', ''), len(a['results'])))
    out.append('- 개선 후 `%s` (%d건)' % (b['config'].get('name', ''), len(b['results'])))
    out.append('')
    out.append('막대 그래프용 값')
    out.append('```')
    for k in keys:
        if k in tb:
            out.append('%s\t%.1f\t%.1f' % (k, ta[k]['rate'], tb[k]['rate']))
    out.append('```')
    return '\n'.join(out)


def main():
    argv = sys.argv[1:]
    override = None
    if '--scorers' in argv:
        i = argv.index('--scorers')
        override = [x for x in argv[i + 1].split(',') if x]
        del argv[i:i + 2]
    refresh = '--refresh-key' in argv
    if refresh:
        argv.remove('--refresh-key')
    args = [a for a in argv if not a.startswith('-')]
    if not args:
        print(__doc__)
        return 1
    if len(args) == 1:
        run = load(args[0])
        if refresh:
            n = refresh_key(run)
            print('  정답 열 %d칸을 지금 평가셋에서 다시 읽었다' % n)
        text = md_one(run, grade(run, override))
    else:
        a, b = load(args[0]), load(args[1])
        text = md_compare(a, grade(a, override), b, grade(b, override))
    print(text)
    out = os.path.join(HERE, 'runs', 'report.md')
    io.open(out, 'w', encoding='utf-8', newline='').write(text + '\n')
    print('\n-> %s' % os.path.relpath(out, HERE))
    return 0


if __name__ == '__main__':
    sys.exit(main())
