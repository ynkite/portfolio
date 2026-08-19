# -*- coding: utf-8 -*-
"""조판한 쪽을 이미지로 뽑는다. 숫자가 아니라 눈으로 확인하기 위한 도구다.

사용 — python tools/pageshot.py [_pdf.html] [출력폴더] [한장에담을쪽수]
"""
import io
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfkit import CHROME

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PW, PH = 1123, 793


def split_pages(html):
    head = html[:html.index('<body')]
    body = html[html.index('>', html.index('<body')) + 1:html.rindex('</body>')]
    pages, i = [], 0
    while True:
        i = body.find('<section class="page', i)
        if i < 0:
            break
        depth, j = 0, i
        for m in re.finditer(r'<section\b|</section>', body[i:]):
            if m.group(0).startswith('</'):
                depth -= 1
                if depth == 0:
                    j = i + m.end()
                    break
            else:
                depth += 1
        pages.append(body[i:j])
        i = j
    return head, pages


SHEET_CSS = '''<style>
html,body{background:#8a8a8a;margin:0}
.sheet{display:grid;grid-template-columns:repeat(%d,%dpx);gap:14px;padding:14px}
.cell{position:relative}
.cell .page{break-after:auto!important;box-shadow:none}
.cell .no{position:absolute;left:0;top:-13px;font:700 11px/1 monospace;color:#fff}
</style>'''


def sheets(src, outdir, per=4, cols=2):
    html = io.open(src, encoding='utf-8').read()
    head, pages = split_pages(html)
    os.makedirs(outdir, exist_ok=True)
    rows = (per + cols - 1) // cols
    made = []
    for s in range(0, len(pages), per):
        part = pages[s:s + per]
        cells = ''.join('<div class="cell"><div class="no">p%02d</div>%s</div>'
                        % (s + k + 1, p) for k, p in enumerate(part))
        # 자산 경로가 상대경로다. 반드시 문서와 같은 폴더에서 열어야 사진이 뜬다
        tmp = os.path.join(os.path.dirname(os.path.abspath(src)), '_sheet.html')
        io.open(tmp, 'w', encoding='utf-8', newline='').write(
            head + (SHEET_CSS % (cols, PW)) + '</head><body class="pdfdoc">'
            '<div class="sheet">' + cells + '</div></body></html>')
        png = os.path.join(outdir, 'sheet-%02d.png' % (s // per + 1))
        w = cols * PW + (cols + 1) * 14
        h = rows * PH + (rows + 1) * 14
        subprocess.run(
            [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
             '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_shot'),
             '--force-device-scale-factor=1', '--hide-scrollbars',
             '--window-size=%d,%d' % (w, h), '--virtual-time-budget=60000',
             '--screenshot=' + png, 'file:///' + tmp.replace('\\', '/')],
            check=True, capture_output=True)
        made.append(png)
        print('  %s  (p%02d-p%02d)' % (os.path.basename(png), s + 1, s + len(part)))
    os.remove(tmp)
    print('쪽 %d장 → 시트 %d장' % (len(pages), len(made)))
    return made


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_pdf.html')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, '_shots')
    per = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    sheets(src, out, per)
