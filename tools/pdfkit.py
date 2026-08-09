# -*- coding: utf-8 -*-
"""페이지를 직접 짜서 PDF를 만드는 조판 도구.

인쇄기에 흐름을 맡기면 카드 한가운데가 잘린다. 그래서 쪼갤 수 없는
덩어리(블록)로 먼저 나누고, 헤드리스 크롬으로 높이를 실측한 뒤,
파이썬에서 한 쪽씩 담아 배치한다. 잘릴 자리가 없어진다.

A4 가로 297×210mm. 여백을 뺀 본문 높이가 한 쪽의 예산이다.
"""
import io
import json
import os
import re
import subprocess

CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'

PAGE_W = 1122.5      # 297mm @96dpi
PAGE_H = 793.7       # 210mm
PAD_T, PAD_B, PAD_X = 48, 60, 64
BODY_H = int(PAGE_H - PAD_T - PAD_B)   # 한 쪽에 담을 수 있는 높이


class Block:
    """한 쪽 안에서 쪼개지지 않는 덩어리."""

    __slots__ = ('html', 'newpage', 'softpage', 'keepnext', 'tag', 'h')

    def __init__(self, html, newpage=False, keepnext=False, tag='', softpage=False):
        self.html = html
        self.newpage = newpage      # 반드시 새 쪽에서 시작
        self.softpage = softpage    # 앞 쪽이 어느 정도 찼을 때만 새 쪽에서 시작
        self.keepnext = keepnext    # 다음 블록과 떨어지면 안 된다 (제목)
        self.tag = tag              # 바닥글에 쓸 장 이름
        self.h = 0


# ─────────────────────────── HTML 쪼개기 ───────────────────────────

VOID = {'img', 'br', 'hr', 'input', 'meta', 'link', 'source'}


def split_top(html):
    """최상위 형제 요소들을 문자열 목록으로 자른다."""
    out, i, n = [], 0, len(html)
    while i < n:
        m = re.compile(r'<([a-zA-Z][\w-]*)').search(html, i)
        if not m:
            break
        tag = m.group(1).lower()
        gt = html.index('>', m.end())
        if tag in VOID or html[gt - 1] == '/':
            out.append(html[m.start():gt + 1])
            i = gt + 1
            continue
        depth, j = 1, gt + 1
        pat = re.compile(r'<%s\b|</%s\s*>' % (tag, tag), re.I)
        while depth and j < n:
            k = pat.search(html, j)
            if not k:
                j = n
                break
            depth += -1 if k.group(0).startswith('</') else 1
            j = k.end()
        out.append(html[m.start():j])
        i = j
    return [x for x in out if x.strip()]


def inner(el):
    """요소 하나의 안쪽 HTML."""
    gt = el.index('>')
    close = el.rindex('</')
    return el[gt + 1:close]


def attr(el, name):
    m = re.search(r'%s="([^"]*)"' % name, el[:el.index('>')])
    return m.group(1) if m else ''


# ─────────────────────────── 높이 실측 ───────────────────────────

def measure_html(body, head, tmp, chrome=CHROME):
    """data-bid가 붙은 요소들의 높이를 한 번에 잰다."""
    probe = ('<script>addEventListener("load",function(){var o={};'
             'document.querySelectorAll("[data-bid]").forEach(function(e){'
             'o[e.dataset.bid]=Math.ceil(e.getBoundingClientRect().height)});'
             'document.title="MEAS"+JSON.stringify(o)});</script>')
    css = ('<style>.mpage{width:%dpx;padding:0 %dpx;box-sizing:border-box}'
           '.mblk{overflow:hidden}</style>' % (PAGE_W, PAD_X))
    io.open(tmp, 'w', encoding='utf-8', newline='').write(
        '<!DOCTYPE html><html lang="ko" class="js"><head><meta charset="UTF-8">'
        + head + css + '</head><body class="pdfdoc"><div class="mpage">'
        + body + '</div>' + probe + '</body></html>')
    out = subprocess.run(
        [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_meas'),
         '--window-size=%d,900' % PAGE_W, '--virtual-time-budget=90000',
         '--dump-dom', 'file:///' + tmp.replace('\\', '/')],
        capture_output=True).stdout.decode('utf-8', 'replace')
    m = re.search(r'<title>MEAS(\{.*?\})</title>', out, re.S)
    if not m:
        raise SystemExit('높이 측정 실패')
    return json.loads(m.group(1))


def measure(blocks, head, tmp, chrome=CHROME):
    """블록 목록의 높이를 잰다."""
    body = ''.join('<div class="mblk" data-bid="%d">%s</div>' % (i, b.html)
                   for i, b in enumerate(blocks))
    hs = measure_html(body, head, tmp, chrome)
    for i, b in enumerate(blocks):
        b.h = hs.get(str(i), 0)
    return blocks


# ─────────────────────────── 쪽에 담기 ───────────────────────────

def paginate(blocks, budget=BODY_H):
    """블록을 순서대로 쪽에 담는다. 넘치면 다음 쪽으로 넘긴다."""
    pages, cur, used = [], [], 0
    for i, b in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        need = b.h
        if b.keepnext and nxt:
            # 제목만 덩그러니 남지 않을 만큼만 미리 잡는다. 통째로 잡으면
            # 뒤 블록이 클 때 앞 쪽이 텅 빈 채로 넘어간다
            need += min(nxt.h, budget * .28)
        soft = b.softpage and used > budget * .58
        if cur and (b.newpage or soft or used + need > budget):
            pages.append(cur)
            cur, used = [], 0
        cur.append(b)
        used += b.h
    if cur:
        pages.append(cur)
    return pages


def render_pages(pages, foot_title, budget=BODY_H):
    """쪽마다 바닥글을 달고, 남는 공간은 블록 사이로 나눠 위쪽 쏠림을 없앤다."""
    total = len(pages)
    out = []
    for n, page in enumerate(pages, 1):
        tag = next((b.tag for b in page if b.tag), '')
        bleed = any('cvwrap' in b.html for b in page)
        if bleed:
            out.append('<section class="page bleed">%s</section>'
                       % ''.join(b.html for b in page))
            continue
        brand = ''
        m = re.search(r'--brand:\s*(#[0-9a-fA-F]{3,8})', ''.join(b.html for b in page))
        if m:
            brand = ' style="--brand:%s"' % m.group(1)
        used = sum(b.h for b in page)
        gap = 0
        # 절반도 못 채운 쪽은 일부러 비워 둔 자리다. 억지로 늘리지 않는다
        if len(page) > 1 and budget * .55 < used < budget * .94:
            gap = min((budget - used) / float(len(page) - 1), 34)
        foot = ('<div class="pfoot"><span>%s</span><span>%s</span>'
                '<span>%02d / %02d</span></div>' % (foot_title, tag, n, total))
        out.append('<section class="page"%s><div class="pgbody" style="gap:%.1fpx">%s</div>%s</section>'
                   % (brand, gap, ''.join(b.html for b in page), foot))
    return ''.join(out)


def print_pdf(src, out, chrome=CHROME):
    subprocess.run(
        [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_print'),
         '--no-pdf-header-footer', '--virtual-time-budget=90000',
         '--print-to-pdf=' + out, 'file:///' + src.replace('\\', '/')],
        check=True, capture_output=True)
    d = open(out, 'rb').read()
    return len(d), d.count(b'/Type /Page') - d.count(b'/Type /Pages')
