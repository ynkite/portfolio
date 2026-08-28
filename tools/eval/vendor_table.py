# -*- coding: utf-8 -*-
"""벤더 비교표를 실행 결과와 사용량 로그에서 만들어 상세 페이지에 박는다.

속도·실패율은 실행 결과에서, 토큰·비용은 COGI 의 ai_usage_logs 에서 온다.
둘을 손으로 합치면 어긋나므로 여기서 한 번에 만든다.

  python tools/eval/vendor_table.py            표를 만들어 cogi.html 에 넣는다
  python tools/eval/vendor_table.py --dry      만들어진 표만 보여 준다
"""
import glob
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.abspath(os.path.join(HERE, '..', '..', 'projects', 'cogi.html'))
PROPS = r'E:\daewooproject\COGI\backend\src\main\resources\application.properties'
MARIADB = r'C:\Program Files\MariaDB 12.2\bin\mariadb.exe'

BEGIN = '<!-- vendor:begin -->'
END = '<!-- vendor:end -->'

LABEL = {'claude-haiku-4-5': 'Claude', 'gpt-5.6-luna': 'GPT', 'gemini-3.5-flash': 'Gemini'}


def runs():
    """모델별 성공률·응답 시간. 벤더 비교 실행 파일만 본다."""
    out = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'runs', 'COGI_코드리뷰*.json')),
                    key=os.path.getmtime):
        d = json.loads(io.open(f, encoding='utf-8').read())
        res = d['results']
        if len(res) < 5:                     # 연결 확인용 1~2건짜리는 버린다
            continue
        ok = [r for r in res if not r['error']]
        model = None
        for r in ok:
            try:
                model = json.loads(r['body'])['data']['modelName']
                break
            except Exception:
                pass
        if not model:
            continue
        ms = sorted(r['ms'] for r in ok)
        # 분류 정확도도 같은 응답에서 나온다. 따로 돌릴 필요가 없다
        import scorers
        hit = tot = 0
        for x in res:
            passed, _ = scorers.run_one('cogi_category', x, {})
            if passed is None:
                continue
            tot += 1
            hit += 1 if passed else 0
        out[model] = {
            'n': len(res), 'ok': len(ok),
            'median': ms[len(ms) // 2] if ms else 0,
            'p90': ms[int(len(ms) * .9) - 1] if ms else 0,
            'cat_hit': hit, 'cat_tot': tot,
        }
    return out


def usage():
    """토큰·비용. 코드가 벤더 응답에서 받아 적어 둔 값을 그대로 읽는다."""
    try:
        w = re.search(r'spring\.datasource\.password=(.*)',
                      io.open(PROPS, encoding='utf-8', errors='replace').read()).group(1).strip()
    except Exception:
        return {}
    sql = ("select model_name, round(avg(input_tokens)), round(avg(output_tokens)), "
           "round(avg(cost),4) from ai_usage_logs "
           "where request_type='REVIEW' and created_at >= curdate() - interval 3 day group by model_name;")
    r = subprocess.run([MARIADB, '--default-character-set=utf8mb4', '-u', 'root', '-p' + w,
                        '-D', 'cogi', '-N', '-B', '-e', sql], capture_output=True)
    out = {}
    for line in r.stdout.decode('utf-8', 'replace').splitlines():
        p = line.split('\t')
        if len(p) == 4:
            out[p[0]] = {'in': p[1], 'out': p[2], 'cost': p[3]}
    return out


def rows():
    rn, us = runs(), usage()
    out = []
    for model in ('claude-haiku-4-5', 'gpt-5.6-luna', 'gemini-3.5-flash'):
        r, u = rn.get(model), us.get(model)
        if not r:
            continue
        rate = '%.0f%%' % (100.0 * r['ok'] / r['n'])
        tok = ('%s / %s' % (u['in'], u['out'])) if u else '—'
        cost = ('$%s' % u['cost']) if u else '—'
        cat = ('%.0f%% <span class="ch">(%d/%d)</span>' % (100.0 * r['cat_hit'] / r['cat_tot'],
                                                          r['cat_hit'], r['cat_tot'])) if r['cat_tot'] else '—'
        out.append([LABEL.get(model, model), '~<code>%s</code>' % model,
                    '%s <span class="ch">(%d/%d)</span>' % (rate, r['ok'], r['n']),
                    cat,
                    '%s초' % round(r['median'] / 1000.0, 1), '~' + tok, cost])
    return out


def html(rs):
    head = ['벤더', '모델', '성공률', '분류 정확도', '응답 중앙값', '입력/출력 토큰', '1건당 비용']
    o = ['      <table class="evt">', '        <thead>', '          <tr>']
    o += ['            <th>%s</th>' % h for h in head]
    o += ['          </tr>', '        </thead>', '        <tbody>']
    for r in rs:
        o.append('          <tr>')
        for i, c in enumerate(r):
            k = ' class="nm"' if i == 0 else (' class="ch"' if c.startswith('~') else '')
            o.append('            <td%s>%s</td>' % (k, c.lstrip('~')))
        o.append('          </tr>')
    o += ['        </tbody>', '      </table>']
    return '\n'.join(o)


def main():
    rs = rows()
    if not rs:
        print('  벤더 비교 실행 결과가 없다')
        return 1
    table = html(rs)
    if '--dry' in sys.argv:
        print(table)
        return 0
    s = io.open(PAGE, encoding='utf-8').read()
    if BEGIN not in s or END not in s:
        print('  cogi.html 에 %s / %s 표시가 없다' % (BEGIN, END))
        return 1
    a, b = s.index(BEGIN) + len(BEGIN), s.index(END)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(s[:a] + '\n' + table + '\n      ' + s[b:])
    print('  벤더 %d줄 반영' % len(rs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
