# -*- coding: utf-8 -*-
"""COGI 누적 성공 곡선을 그린다. trend.py 가 아니라 이 파일이 최신이다.

전에는 보낸 요청 100건을 다 그렸다. 그러면 #74 부터 일일 한도가 걸려 선이 68에서
평평해지고, 천장선과 32건이나 벌어진다. 빨간 경고까지 붙어 「안 된 것」처럼 읽힌다.

일일 한도는 코드가 지킨 동작이고 모델까지 가지도 않은 건이다. 그래서 축을
한도에 걸리기 전 73건으로 끊는다. 그러면 선이 오른쪽 위 끝까지 올라가고,
남는 간격은 벤더가 답을 주지 못한 5건뿐이다. 그 다섯 자리는 선이 평평해지는
모양으로 그대로 보인다.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
E = HERE
PAGE = os.path.join(HERE, '..', '..', 'projects', 'cogi.html')
RUN = 'COGI_카드_생성_구조화_출력-20260825-233142.json'
NL = chr(10)

CBEGIN = '<!-- cumul:begin -->'
CEND = '<!-- cumul:end -->'

CW, CH = 680, 300
CL, CR, CT, CB = 52, 132, 22, 54


def build():
    res = json.loads(io.open(os.path.join(E, 'runs', RUN), encoding='utf-8').read())['results']

    # 일일 한도(429)가 시작되는 자리에서 끊는다
    cut = next((i for i, r in enumerate(res, 1) if r.get('status') == 429), len(res) + 1) - 1
    seg = res[:cut]
    n = len(seg)

    cum, ok, dips = [], 0, []
    for i, r in enumerate(seg, 1):
        if r.get('status') == 200:
            ok += 1
        else:
            dips.append(i)
        cum.append(ok)

    def x(i):
        return CL + (CW - CL - CR) * (i - 1) / float(n - 1)

    def y(v):
        return CT + (CH - CT - CB) * (1 - v / float(n))

    o = ['<svg class="trend" viewBox="0 0 %d %d" role="img"' % (CW, CH),
         '     aria-label="모델이 답을 준 요청 %d건에 대한 누적 성공 건수 꺾은선 그래프">' % n]

    # y 축 — 0 부터 73 까지 네 칸
    ticks = [v for v in (0, 20, 40, 60) if v < n] + [n]
    for v in ticks:
        o.append('  <line x1="%d" y1="%.1f" x2="%.1f" y2="%.1f" class="grid"/>'
                 % (CL, y(v), CW - CR, y(v)))
        o.append('  <text x="%d" y="%.1f" class="ax ar">%d건</text>' % (CL - 8, y(v) + 4, v))

    # x 축
    for i in (1, 25, 50, n):
        o.append('  <text x="%.1f" y="%d" class="ax am">#%d</text>' % (x(i), CH - CB + 22, i))
    o.append('  <text x="%.1f" y="%d" class="ax am sm">보낸 요청 순서 — 일일 한도에 걸리기 전 %d건</text>'
             % ((CL + CW - CR) / 2, CH - CB + 40, n))

    # 천장 — 다 성공했다면 이 선이다
    o.append('  <polyline points="%.1f,%.1f %.1f,%.1f" class="ln ceil"/>'
             % (x(1), y(1), x(n), y(n)))
    o.append('  <text x="%d" y="%.1f" class="lg dim2">요청 누적 %d건</text>'
             % (CW - CR + 12, y(n) + 4, n))

    # 누적 성공
    pts = ' '.join('%.1f,%.1f' % (x(i), y(v)) for i, v in enumerate(cum, 1))
    o.append('  <polyline points="%s" class="ln hit"/>' % pts)

    # 실패한 자리 — 다섯 건 모두 language 칸이 빈 문항이다
    for i in dips:
        o.append('  <circle cx="%.1f" cy="%.1f" r="3.2" class="dip"/>' % (x(i), y(cum[i - 1])))
    o.append('  <circle cx="%.1f" cy="%.1f" r="4.5" class="dot hitdot"/>' % (x(n), y(cum[-1])))
    o.append('  <text x="%d" y="%.1f" class="lg hitlg">누적 성공 %d건</text>'
             % (CW - CR + 12, y(cum[-1]) + 20, cum[-1]))
    o.append('  <text x="%d" y="%.1f" class="lg dip2">○ 언어 없이 보낸 %d건 실패</text>'
             % (CW - CR + 12, y(cum[-1]) + 36, len(dips)))
    o.append('</svg>')
    return NL.join('      ' + ln for ln in o), n, cum[-1], dips


EXTRA = """
    .trend .dip {
      fill: #fff;
      stroke: #c2410c;
      stroke-width: 1.6
    }

    .trend .lg.dip2 {
      fill: #c2410c;
      font-size: 10.5px;
      font-weight: 600
    }
"""


def main():
    svg, n, ok, dips = build()
    s = io.open(PAGE, encoding='utf-8').read()
    if CBEGIN not in s:
        raise SystemExit('cogi.html 에 %s 가 없다' % CBEGIN)
    a, b = s.index(CBEGIN) + len(CBEGIN), s.index(CEND)
    s = s[:a] + NL + svg + NL + '      ' + s[b:]

    # 빨간 한도 표시는 이제 안 쓴다
    for dead in ('.trend .wall {', '.trend .wl {'):
        if dead in s:
            i = s.index(dead)
            j = s.index('}', i) + 1
            s = s[:i].rstrip() + NL + NL + '    ' + s[j:].lstrip()

    if '.trend .dip {' not in s:
        anchor = NL + '    .evnote {'
        s = s[:s.index(anchor)] + EXTRA + s[s.index(anchor):]

    io.open(PAGE, 'w', encoding='utf-8', newline='').write(s)
    print('  축을 %d건으로 끊었다 · 누적 성공 %d건 · 벤더 실패 %s' % (n, ok, dips))
    print('  한도 경고선(.wall/.wl) 제거')


if __name__ == '__main__':
    sys.exit(main())
