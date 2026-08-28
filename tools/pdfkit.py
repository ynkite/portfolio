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
PAD_T, PAD_B, PAD_X = 82, 60, 64
SAFETY = 18   # 실측과 인쇄 사이의 미세한 오차분. 이만큼 비워 두면 잘리지 않는다
BODY_H = int(PAGE_H - PAD_T - PAD_B) - SAFETY


class Block:
    """한 쪽 안에서 쪼개지지 않는 덩어리."""

    __slots__ = ('html', 'newpage', 'softpage', 'keepnext', 'tag', 'head', 'h', 'fixh', 'grp')

    def __init__(self, html, newpage=False, keepnext=False, tag='', softpage=False,
                 head=None, fixh=0, grp=''):
        self.html = html
        self.newpage = newpage      # 반드시 새 쪽에서 시작
        self.softpage = softpage    # 앞 쪽이 어느 정도 찼을 때만 새 쪽에서 시작
        self.keepnext = keepnext    # 다음 블록과 떨어지면 안 된다 (제목)
        self.tag = tag              # 바닥글에 쓸 장 이름
        self.head = head            # 이어지는 쪽 머리에 쓸 (절 라벨, 절 이름)
        self.fixh = fixh            # 실측 대신 쓸 높이. 지면을 채우는 블록에 쓴다
        self.grp = grp              # 같은 절. 한 쪽에 들어갈 만하면 통째로 넘긴다
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
    # 글꼴이 붙은 뒤에 재야 한다. 대체 글꼴로 재면 인쇄본과 높이가 어긋나 잘린다
    probe = ('<script>addEventListener("load",function(){'
             'document.fonts.ready.then(function(){var o={};'
             'document.querySelectorAll("[data-bid]").forEach(function(e){'
             'o[e.dataset.bid]=Math.ceil(e.getBoundingClientRect().height)});'
             'document.title="MEAS"+JSON.stringify(o)})});</script>')
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
        # 지면을 채우는 블록은 실측값이 아니라 정해 둔 높이를 쓴다.
        # 자연 높이로 재면 남는 자리만큼 뒤 블록이 딸려 들어와 지면이 무너진다
        b.h = b.fixh or hs.get(str(i), 0)
    return blocks


# ─────────────────────────── 쪽에 담기 ───────────────────────────

def paginate(blocks, budget=BODY_H):
    """블록을 순서대로 쪽에 담는다. 넘치면 다음 쪽으로 넘긴다."""
    # 한 쪽에 들어갈 만한 절은 통째로 넘긴다. 절반만 앞 쪽에 걸치면
    # 앞뒤 어디에도 속하지 않은 채 잘린 것처럼 읽힌다
    gh = {}
    for b in blocks:
        if b.grp:
            gh[b.grp] = gh.get(b.grp, 0) + b.h

    pages, cur, used = [], [], 0
    for i, b in enumerate(blocks):
        nxt = blocks[i + 1] if i + 1 < len(blocks) else None
        opens = b.grp and (i == 0 or blocks[i - 1].grp != b.grp)
        need = b.h
        if opens and gh[b.grp] <= budget:
            need = gh[b.grp]
        elif b.keepnext and nxt:
            # 제목이 혼자 남는 쪽을 만들지 않는다. 뒤 블록의 절반까지 미리 잡아
            # 제목 한 줄짜리 쪽이 생기지 않게 한다
            need += min(nxt.h, budget * .62)
        soft = b.softpage and used > budget * .58
        if cur and (b.newpage or soft or used + need > budget):
            pages.append(cur)
            cur, used = [], 0
        cur.append(b)
        used += b.h
    if cur:
        pages.append(cur)
    return balance(pages, budget)


def balance(pages, budget):
    """한 절이 두 쪽에 걸치면 두 쪽의 채움을 고르게 맞춘다.

    앞 쪽만 꽉 차고 뒤 쪽에 한 덩어리만 남으면, 뒤 쪽은 앞에서 잘려 나온
    자투리처럼 읽힌다. 같은 절 안에서만 뒤로 넘겨 균형을 맞춘다.
    """
    for a, b in zip(pages, pages[1:]):
        if not a or not b or b[0].newpage:
            continue
        while len(a) > 1:
            mv = a[-1]
            # 절이 다르거나 제목이면 옮기지 않는다
            if not mv.grp or mv.grp != b[0].grp or mv.keepnext:
                break
            ha, hb = sum(x.h for x in a), sum(x.h for x in b)
            if hb + mv.h > budget or abs(ha - mv.h - hb - mv.h) >= abs(ha - hb):
                break
            b.insert(0, a.pop())
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
        # 절 머리가 없는 쪽에는 어디까지 왔는지 한 줄 얹는다.
        # 흘러가는 문서가 아니라 한 판으로 읽히게 하는 장치다
        lead_in = ''
        if 'class="sechd"' not in page[0].html and page[0].head:
            lead_in = ('<div class="runhd"><span class="step">%s</span>'
                       '<span>%s</span></div>' % page[0].head)
        used = sum(b.h for b in page)
        # 남은 자리를 블록 사이로 흘려 아래가 텅 비지 않게 한다.
        # 다만 벌어진 틈이 단락 사이 여백으로 읽히는 선을 넘지는 않는다.
        # 덜 찬 쪽일수록 조금 더 벌린다
        gap = 0
        if len(page) > 1 and used < budget * .97:
            # 표 행 사이를 너무 벌리면 한 표가 아니라 따로 노는 항목으로 읽힌다
            cap = 40 if used < budget * .62 else 32
            gap = min((budget - used) / float(len(page) - 1), cap)
        # 더 담을 수 없는 쪽은 위로 붙이지 않고 지면 한가운데 앉힌다.
        # 그래야 남은 자리가 미완성이 아니라 의도한 여백으로 읽힌다.
        # 다만 본문이 딸린 절은 제목이 늘 같은 높이에서 시작해야 하므로
        # 덩어리 하나뿐인 쪽과 절 머리만 놓인 쪽에만 적용한다
        heads_only = all('class="sechd"' in b.html for b in page)
        # 절 제목은 쪽마다 같은 높이에서 시작해야 한다. 어떤 절은 위에서,
        # 어떤 절은 한가운데서 시작하면 넘길 때마다 제목이 튄다.
        # 절 머리만 놓인 쪽은 예외 — 거기엔 기준이 될 본문이 없다
        opens_section = 'class="sechd"' in page[0].html and not heads_only
        lone = len(page) == 1 and 'class="sechd"' not in page[0].html
        mid = ('justify-content:center;'
               if budget * .3 < used < budget * .97 and not opens_section
               and (used < budget * .5 or lone or heads_only) else '')
        foot = ('<div class="pfoot"><span>%s</span><span>%s</span>'
                '<span>%02d / %02d</span></div>' % (foot_title, tag, n, total))
        out.append('<section class="page"%s>%s<div class="pgbody" style="%sgap:%.1fpx">%s</div>%s</section>'
                   % (brand, lead_in, mid, gap, ''.join(b.html for b in page), foot))
    return ''.join(out)


LIMIT = int(PAGE_H - PAD_T - PAD_B)   # 실제로 쓸 수 있는 높이. 여기를 넘으면 잘린다


def assert_fits(src, budget=None, chrome=CHROME):
    """인쇄 직전에 쪽마다 실제 높이를 재어 넘치는 쪽이 없는지 확인한다."""
    budget = budget or LIMIT
    # 본문 상자에 높이를 못 박아 두었으므로 상자 자체의 높이를 재면 언제나
    # 예산과 같게 나온다. 넘친 내용은 상자 밖으로 흘러 잘릴 뿐이다.
    # 그래서 상자가 아니라 자식들의 아래 끝을 재야 진짜 넘침이 보인다
    # 쪽 번호로 세어야 한다. 표지에는 .pgbody 가 없어서 .pgbody 로 세면
    # 그 뒤 쪽 번호가 전부 하나씩 밀린 채 보고된다
    probe = ('<script>addEventListener("load",function(){document.fonts.ready.then(function(){'
             'var o=[];document.querySelectorAll(".page").forEach(function(p,i){'
             'var e=p.querySelector(".pgbody");if(!e)return;'
             'var top=e.getBoundingClientRect().top,b=0;'
             'e.querySelectorAll("*").forEach(function(c){'
             # 일부러 잘라 보여 주는 상자(산출물 미리보기) 안쪽은 세지 않는다.
             # 그 안에서 넘치는 건 설계한 자름이지 사고가 아니다
             'for(var p=c.parentNode;p&&p!==e;p=p.parentNode){'
             'if(getComputedStyle(p).overflowY!=="visible")return}'
             'var r=c.getBoundingClientRect();if(r.height&&r.bottom>b)b=r.bottom});'
             'var h=Math.ceil(Math.max(b-top,e.getBoundingClientRect().height));'
             'if(h>%d)o.push((i+1)+":"+h)});'
             'document.title="FIT["+o.join(",")+"]"})});</script>' % budget)
    tmp = src.replace('.html', '_fit.html')
    io.open(tmp, 'w', encoding='utf-8', newline='').write(
        io.open(src, encoding='utf-8').read().replace('</body>', probe + '</body>'))
    out = subprocess.run(
        [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_fit'),
         '--window-size=%d,%d' % (PAGE_W, PAGE_H), '--virtual-time-budget=90000',
         '--dump-dom', 'file:///' + tmp.replace(os.sep, '/')],
        capture_output=True).stdout.decode('utf-8', 'replace')
    os.remove(tmp)
    m = re.search(r'<title>FIT\[(.*?)\]</title>', out, re.S)
    bad = [x for x in (m.group(1).split(',') if m and m.group(1) else []) if x]
    return bad


def print_pdf(src, out, chrome=CHROME, expect=0):
    """인쇄한다. 뷰어가 결과 파일을 열고 있으면 크롬은 조용히 실패하고
    종료 코드 0을 준다. 그대로 두면 예전 파일을 읽고 "완료"로 보고하게 된다.
    그래서 임시 파일로 뽑은 뒤 옮기고, 쪽 수까지 대조한다."""
    tmp = out + '.new'
    if os.path.exists(tmp):
        os.remove(tmp)
    subprocess.run(
        [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
         '--user-data-dir=' + os.path.join(os.environ.get('TEMP', '.'), 'cr_print'),
         # 이걸 빼면 크롬이 쪽 오른쪽에 스크롤바를 그려 넣는다.
         # 인쇄물에 스크롤바가 찍히면 「캡처해 붙인 것」처럼 보인다
         '--hide-scrollbars',
         '--window-size=%d,%d' % (int(PAGE_W), int(PAGE_H)),
         '--no-pdf-header-footer', '--virtual-time-budget=90000',
         '--print-to-pdf=' + tmp, 'file:///' + src.replace('\\', '/')],
        check=True, capture_output=True)
    if not os.path.exists(tmp):
        raise SystemExit('인쇄 실패 — 크롬이 %s 를 만들지 못했다' % tmp)
    d = open(tmp, 'rb').read()
    pages = len(re.findall(rb'/MediaBox', d))
    if expect and pages != expect:
        raise SystemExit('쪽 수가 어긋난다 — 조판 %d쪽, 인쇄 %d쪽' % (expect, pages))
    try:
        os.replace(tmp, out)
    except OSError:
        raise SystemExit(
            '결과 파일이 잠겨 있다 — %s 를 여는 뷰어를 닫고 다시 실행할 것.\n'
            '        새로 뽑은 판은 %s 에 두었다.' % (out, tmp))
    return len(d), pages
