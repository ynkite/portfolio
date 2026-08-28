# -*- coding: utf-8 -*-
"""회차별 추이를 꺾은선 그래프(SVG)로 그려 상세 페이지에 박는다.

세 번의 실행을 지금 채점기로 다시 채점해 같은 기준으로 세운다.
실행 당시 채점기가 서로 달랐으므로, 다시 채점하지 않으면 비교가 성립하지 않는다.

  python tools/eval/trend.py         그래프를 그려 넣는다
  python tools/eval/trend.py --dry   SVG 만 출력한다

값은 `runs/` 에 남은 응답에서만 온다. API 를 다시 부르지 않는다.
"""
import io
import json
import os
import sys

import scorers

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..', '..'))
RUNS = os.path.join(HERE, 'runs')
NL = chr(10)                          # 스크립트로 이 파일을 고칠 때 줄바꿈이 깨지지 않게

PAGE = os.path.join(SITE, 'projects', 'triplinker.html')
BEGIN = '<!-- trend:begin -->'
END = '<!-- trend:end -->'

# 회차 — 파일 이름을 박아 둔다. 어느 실행이 몇 회차인지는 사람이 정해야 한다
STAMPS = [
    ('1', '2026.08.25', 'TripLinker_경로_생성_실재성_타당성-20260825-225907.json'),
    ('2', '2026.08.26', 'TripLinker_경로_생성_실재성_타당성-20260826-200604.json'),
    ('3', '2026.08.26', 'TripLinker_경로_생성_실재성_타당성-20260826-204047.json'),
]

# 그릴 지표. 세 회차 모두 100% 인 것(장소 실재율·일수 일치·동선 상한)은 선이 겹쳐 빼놨다
# 요청 성공률은 세 회차 모두 일정 생성률과 값이 같다(실패가 전부 생성 실패였다).
# 선이 완전히 겹치므로 그리지 않는다.
SERIES = [
    ('일정 생성률', 'tl_generated', '#c2410c'),
    ('예산 준수율', 'tl_budget', '#6b7280'),
]

W, H = 680, 320
L, R, T, B = 46, 132, 20, 52          # 안쪽 여백


# 벤더 한도에 걸린 요청은 HTTP 200 으로 빈 일정이 돌아온다. 모델을 부르지도 못한 건이라
# 생성 능력의 분모에서 뺀다. 판정 근거는 응답 시간이다 — 실제로 만들어 낸 건은 16~44초,
# 한도에 걸린 건은 1.3~1.7초다. 지면의 「요청 100건의 내역」 표와 같은 기준이다.
FAST_MS = 5000


def _answered(r):
    return not (r.get('status') == 200 and r.get('ms', 0) < FAST_MS)


def score(path, name):
    run = json.loads(io.open(os.path.join(RUNS, path), encoding='utf-8').read())
    sch = json.loads(io.open(os.path.join(HERE, 'schemas.json'), encoding='utf-8').read())
    ok = n = 0
    for r in run['results']:
        if not _answered(r):
            continue
        passed, _ = scorers.run_one(name, r, sch)
        if passed is None:
            continue
        n += 1
        ok += 1 if passed else 0
    return ok, n


def svg():
    pts = {}
    for label, name, _c in SERIES:
        pts[name] = [score(f, name) for _n, _d, f in STAMPS]

    def x(i):
        return L + (W - L - R) * i / (len(STAMPS) - 1)

    def y(v):
        return T + (H - T - B) * (1 - v / 100.0)

    o = ['<svg class="trend" viewBox="0 0 %d %d" role="img"' % (W, H),
         '     aria-label="회차별 통과율 추이 꺾은선 그래프">']

    # 가로 격자와 y 축 눈금
    for v in (0, 25, 50, 75, 100):
        o.append('  <line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>'
                 % (L, y(v), W - R, y(v)))
        o.append('  <text x="%d" y="%.1f" class="ax ar">%d%%</text>' % (L - 8, y(v) + 4, v))

    # x 축 눈금
    for i, (num, date, _f) in enumerate(STAMPS):
        o.append('  <text x="%.1f" y="%d" class="ax am">%s회차</text>' % (x(i), H - B + 22, num))
        o.append('  <text x="%.1f" y="%d" class="ax am sm">%s</text>' % (x(i), H - B + 38, date))

    # 선과 점
    for label, name, color in SERIES:
        vals = [(100.0 * a / b if b else 0) for a, b in pts[name]]
        d = ' '.join('%.1f,%.1f' % (x(i), y(v)) for i, v in enumerate(vals))
        o.append('  <polyline points="%s" class="ln" style="stroke:%s"/>' % (d, color))
        for i, v in enumerate(vals):
            o.append('  <circle cx="%.1f" cy="%.1f" r="4" class="dot" style="fill:%s"/>'
                     % (x(i), y(v), color))
            # 값은 점 위에. 마지막 점만 굵게
            cls = 'val last' if i == len(vals) - 1 else 'val'
            o.append('  <text x="%.1f" y="%.1f" class="%s" style="fill:%s">%.0f%%</text>'
                     % (x(i), y(v) - 11, cls, color, v))
        # 오른쪽에 이름
        o.append('  <text x="%d" y="%.1f" class="lg" style="fill:%s">%s</text>'
                 % (W - R + 12, y(vals[-1]) + 4, color, label))

    o.append('</svg>')
    return '\n'.join('      ' + ln for ln in o)


CSS = '''
    /* 회차별 추이 꺾은선 */
    .trend {
      width: 100%;
      height: auto;
      display: block;
      margin-top: 6px;
      overflow: visible
    }

    .trend .grid {
      stroke: var(--line);
      stroke-width: 1
    }

    .trend .ln {
      fill: none;
      stroke-width: 2.2;
      stroke-linejoin: round;
      stroke-linecap: round
    }

    .trend .ax {
      font-size: 11px;
      fill: var(--muted)
    }

    .trend .ax.ar {
      text-anchor: end
    }

    .trend .ax.am {
      text-anchor: middle
    }

    .trend .ax.sm {
      font-size: 10px
    }

    .trend .val {
      font-size: 11.5px;
      font-weight: 600;
      text-anchor: middle
    }

    .trend .val.last {
      font-size: 13px;
      font-weight: 700
    }

    .trend .lg {
      font-size: 11.5px;
      font-weight: 600
    }
'''


def add_css(s):
    if '.trend {' in s:
        return s
    anchor = '\n    .evnote {'
    i = s.index(anchor)
    return s[:i] + CSS + s[i:]



# ══════════════ COGI 누적 성공 곡선 ══════════════
# 회차가 하나뿐이라 회차별 추이를 그릴 수 없다. 대신 요청 순서에 따른 누적 성공을 그린다.
# 한도에 걸리는 자리에서 선이 평평해지므로, 「한도만 아니면 다 통과했다」를 말이 아니라 모양으로 보인다.
COGI_PAGE = os.path.join(SITE, 'projects', 'cogi.html')
CBEGIN = '<!-- cumul:begin -->'
CEND = '<!-- cumul:end -->'
COGI_RUN = 'COGI_카드_생성_구조화_출력-20260825-233142.json'

CW, CH = 680, 300
CL, CR, CT, CB = 46, 128, 20, 50


# 이 함수는 scratchpad/cumul2.py 로 대체됐다
# 축을 일일 한도 전 73건으로 끊는 판이 최신이다. trend.py --dry 로 되돌리지 말 것
def cumul_svg():
    run = json.loads(io.open(os.path.join(RUNS, COGI_RUN), encoding='utf-8').read())
    res = run['results']
    n = len(res)
    cum, ok = [], 0
    wall = None
    for i, r in enumerate(res, 1):
        st = r.get('status')
        if st == 200:
            ok += 1
        if st == 429 and wall is None:
            wall = i
        cum.append(ok)

    def x(i):
        return CL + (CW - CL - CR) * (i - 1) / (n - 1)

    def y(v):
        return CT + (CH - CT - CB) * (1 - v / float(n))

    o = ['<svg class="trend" viewBox="0 0 %d %d" role="img"' % (CW, CH),
         '     aria-label="요청 순서에 따른 누적 성공 건수 꺾은선 그래프">']
    for v in (0, 25, 50, 75, 100):
        o.append('  <line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>' % (CL, y(v), CW - CR, y(v)))
        o.append('  <text x="%d" y="%.1f" class="ax ar">%d건</text>' % (CL - 8, y(v) + 4, v))
    for i in (1, 25, 50, 75, 100):
        o.append('  <text x="%.1f" y="%d" class="ax am">#%d</text>' % (x(i), CH - CB + 22, i))
    o.append('  <text x="%.1f" y="%d" class="ax am sm">요청 순서</text>'
             % ((CL + CW - CR) / 2, CH - CB + 40))

    # 한도에 걸린 자리
    if wall:
        o.append('  <line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="wall"/>'
                 % (x(wall), y(0), x(wall), y(n)))
        o.append('  <text x="%.1f" y="%.1f" class="wl">#%d 부터 일일 한도 초과</text>'
                 % (x(wall) + 6, y(n) + 12, wall))

    # 요청 수 (닿을 수 있었던 천장)
    o.append('  <polyline points="%s" class="ln ceil"/>' % ('%.1f,%.1f %.1f,%.1f' % (x(1), y(1), x(n), y(n))))
    o.append('  <text x="%d" y="%.1f" class="lg dim2">요청 누적</text>' % (CW - CR + 12, y(n) + 4))

    # 누적 성공
    pts = ' '.join('%.1f,%.1f' % (x(i), y(v)) for i, v in enumerate(cum, 1))
    o.append('  <polyline points="%s" class="ln hit"/>' % pts)
    o.append('  <circle cx="%.1f" cy="%.1f" r="4" class="dot hitdot"/>' % (x(n), y(cum[-1])))
    o.append('  <text x="%d" y="%.1f" class="lg hitlg">누적 성공 %d건</text>'
             % (CW - CR + 12, y(cum[-1]) + 4, cum[-1]))
    o.append('</svg>')
    return NL.join('      ' + ln for ln in o)


CCSS = """
    .trend .ln.ceil {
      stroke: var(--line);
      stroke-width: 1.6;
      stroke-dasharray: 5 5
    }

    .trend .ln.hit {
      stroke: var(--teal, var(--brand, #0066cc));
      stroke-width: 2.4
    }

    .trend .dot.hitdot {
      fill: var(--teal, var(--brand, #0066cc))
    }

    .trend .wall {
      stroke: #c2410c;
      stroke-width: 1.4;
      stroke-dasharray: 3 4
    }

    .trend .wl {
      font-size: 11px;
      font-weight: 700;
      fill: #c2410c
    }

    .trend .lg.hitlg {
      fill: var(--teal, var(--brand, #0066cc))
    }

    .trend .lg.dim2 {
      fill: var(--muted);
      font-weight: 500
    }
"""


def put_cumul():
    s = io.open(COGI_PAGE, encoding='utf-8').read()
    if CBEGIN not in s:
        print('  cogi.html 에 %s 표시가 없다' % CBEGIN)
        return 1
    a, b = s.index(CBEGIN) + len(CBEGIN), s.index(CEND)
    s = s[:a] + NL + cumul_svg() + NL + '      ' + s[b:]
    anchor = NL + '    .evnote {'
    if '.trend {' not in s:
        s = s[:s.index(anchor)] + CSS + s[s.index(anchor):]
    if '.ln.ceil' not in s:
        s = s[:s.index(anchor)] + CCSS + s[s.index(anchor):]
    io.open(COGI_PAGE, 'w', encoding='utf-8', newline='').write(s)
    print('  COGI 누적 곡선 반영')
    return 0


def main():
    body = svg()
    if '--dry' in sys.argv:
        print(body)
        return 0
    s = io.open(PAGE, encoding='utf-8').read()
    if BEGIN not in s or END not in s:
        print('  %s 에 %s / %s 표시가 없다' % (os.path.basename(PAGE), BEGIN, END))
        return 1
    a, b = s.index(BEGIN) + len(BEGIN), s.index(END)
    s = s[:a] + '\n' + body + '\n      ' + s[b:]
    s = add_css(s)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(s)
    print('  꺾은선 그래프 반영 (%d개 선 × %d회차)' % (len(SERIES), len(STAMPS)))
    # COGI 누적 곡선은 cumul.py 가 그린다. 여기서 부르면 옛 판(요청 100건)으로 되돌아간다
    print('  COGI 누적 곡선은 python tools/eval/cumul.py 로 그린다')
    return 0


if __name__ == '__main__':
    sys.exit(main())
