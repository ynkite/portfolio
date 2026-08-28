# -*- coding: utf-8 -*-
"""웹 표준 감사 결과를 메인 페이지에 박는다.

이 숫자는 프로젝트가 아니라 이 사이트 자체의 품질이라 상세 페이지가 아닌 메인에 둔다.
값은 report.json(현재)과 report-before.json(고치기 전)에서만 온다.

  python tools/audit/publish_audit.py
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.abspath(os.path.join(HERE, '..', '..'))
PAGE = os.path.join(SITE, 'index.html')
BEGIN = '<!-- audit:begin -->'
END = '<!-- audit:end -->'

ROWS = [('performance', '성능'), ('accessibility', '접근성'),
        ('bestPractices', '모범사례'), ('seo', 'SEO')]


def load(name):
    p = os.path.join(HERE, name)
    return json.loads(io.open(p, encoding='utf-8').read()) if os.path.exists(p) else None


def build():
    now, before = load('report.json'), load('report-before.json')
    if not now:
        return None
    a = (before or {}).get('summary', {})
    b = now['summary']
    # 실행마다 흔들리는 지표에 전후 화살표를 붙이면 안 된다.
    # 편차 안에서 움직인 걸 개선이라고 적으면 거짓말이 된다.
    def spread(d, key):
        lo = hi = None
        for v in d['pages'].values():
            sp = v['lighthouse'].get('spread', {}).get(key)
            if not sp:
                continue
            x, y = (int(t) for t in sp.split('~'))
            lo = x if lo is None else min(lo, x)
            hi = y if hi is None else max(hi, y)
        return (lo, hi) if lo is not None else None

    cells = []
    for key, label in ROWS:
        was, is_ = a.get(key), b.get(key)
        sp = spread(now, key)
        stable = sp is None or sp[1] - sp[0] <= 2
        moved = was is not None and is_ != was and stable
        cells.append(
            '        <div class="c"><b%s>%s</b><span>%s%s</span></div>'
            % (' class="up"' if moved else '', is_, label,
               ' <i>%s→%s</i>' % (was, is_) if moved else ''))
    # HTML 오류는 같은 파일을 다시 재도 같은 값이 나온다. 여기엔 화살표를 붙여도 거짓이 아니다
    was_html = a.get('htmlErrors')
    moved_html = was_html is not None and was_html != b['htmlErrors']
    cells.append(
        '        <div class="c"><b%s>%d</b><span>W3C HTML 오류%s</span></div>'
        % (' class="up"' if moved_html else '', b['htmlErrors'],
           ' <i>%d→%d</i>' % (was_html, b['htmlErrors']) if moved_html else ''))
    lo, hi = spread(now, 'performance') or (0, 0)

    return (
        '      <div class="audit rv d2">\n'
        '        <h3>이 사이트를 표준 도구로 잰 값</h3>\n'
        '        <div class="acells">\n%s\n        </div>\n'
        '        <p class="anote">Lighthouse 를 쪽마다 %d번 돌려 중앙값을 쓴 값입니다. %d개 쪽 평균 · 데스크톱 기준.'
        '<br>화살표는 손보기 전후입니다. 앞 값은 손대지 않은 원본 지면을 같은 도구로 다시 재서 얻었습니다.'
        ' 성능은 같은 쪽을 다시 재도 %d~%d로 흔들려 전후를 비교하지 않았습니다.</p>\n'
        '      </div>' % ('\n'.join(cells), b.get('runs', 3), b['pages'], lo, hi))


CSS = '''    /* 표준 도구로 잰 사이트 점수 */
    .audit {
      margin-top: clamp(14px, 2.2vh, 28px);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: clamp(14px, 2vh, 20px) 22px;
      text-align: left
    }

    .audit h3 {
      font-size: 12px;
      font-weight: 600;
      color: #68686d;
      margin-bottom: 12px
    }

    .acells {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px
    }

    .acells .c b {
      display: block;
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -.02em
    }

    .acells .c b.up {
      color: var(--blue)
    }

    .acells .c span {
      font-size: 12px;
      color: #68686d
    }

    .acells .c i {
      font-style: normal;
      color: var(--blue)
    }

    .anote {
      margin-top: 12px;
      font-size: 12px;
      color: #68686d
    }

    @media(max-width:760px) {
      .acells {
        grid-template-columns: 1fr 1fr
      }
    }

'''


def main():
    block = build()
    if not block:
        print('  감사 결과 파일이 없다')
        return 1
    s = io.open(PAGE, encoding='utf-8').read()
    if '.audit {' not in s:
        s = s.replace('    .wrap {', CSS + '    .wrap {', 1)
    if BEGIN not in s:
        # 「링크 · 연락처」 절에 둔다. 프로필 절은 이미 한 화면이 꽉 차 있어 넣으면 넘친다
        m = re.search(r'<div class="archcards[^"]*"[^>]*>', s)
        if not m:
            print('  넣을 자리를 못 찾았다')
            return 1
        s = s[:m.start()] + BEGIN + '\n' + END + '\n      ' + s[m.start():]
    a, b = s.index(BEGIN) + len(BEGIN), s.index(END)
    s = s[:a] + '\n' + block + '\n      ' + s[b:]
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(s)
    print('  index.html 에 감사 결과 반영')
    return 0


if __name__ == '__main__':
    sys.exit(main())
