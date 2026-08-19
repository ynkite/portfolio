# -*- coding: utf-8 -*-
"""쪽 하나만 원본 크기로 뽑는다. 눈으로 자세히 볼 때 쓴다.

사용 — python tools/onepage.py <쪽번호> [오른쪽확대폭]
"""
import io
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdfkit import CHROME
from pageshot import split_pages, PW, PH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

page = int(sys.argv[1])
zoom = int(sys.argv[2]) if len(sys.argv) > 2 else 0

head, pages = split_pages(io.open('_pdf.html', encoding='utf-8').read())
tmp = os.path.join(ROOT, '_one.html')
io.open(tmp, 'w', encoding='utf-8', newline='').write(
    head + '<style>html,body{background:#fff;margin:0}'
           '.page{break-after:auto!important}</style>'
           '</head><body class="pdfdoc">' + pages[page - 1] + '</body></html>')

out = os.path.join(ROOT, '_p%02d.png' % page)
src = 'file:///' + tmp.replace(os.sep, '/')
subprocess.run(
    [CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
     '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_one'),
     '--force-device-scale-factor=1', '--hide-scrollbars',
     '--window-size=%d,%d' % (PW, PH), '--virtual-time-budget=60000',
     '--screenshot=' + out, src], check=True, capture_output=True)
os.remove(tmp)

from PIL import Image
im = Image.open(out)
print('p%02d 렌더 %s -> %s' % (page, im.size, os.path.basename(out)))
if zoom:
    crop = im.crop((PW - zoom, 0, PW, PH))
    crop = crop.resize((zoom * 3, PH * 3), Image.NEAREST)
    z = os.path.join(ROOT, '_p%02d_right.png' % page)
    crop.save(z)
    print('오른쪽 %dpx 를 3배로 -> %s' % (zoom, os.path.basename(z)))
