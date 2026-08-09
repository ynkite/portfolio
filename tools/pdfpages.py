# -*- coding: utf-8 -*-
"""지면용 페이지를 구성한다.

pdfdoc이 뽑아 온 자료를 받아 쪽 단위로 짠다. 쪽마다 담을 개수를 미리
정해 두므로 어느 쪽도 어중간하게 비거나 넘치지 않는다. 컴포넌트는
사이트 것을 그대로 다시 그려 붙여 디자인이 같게 보인다.
"""
import re

from pdfkit import Block

# 격자 한 줄에 들어가는 개수. 쪽에 몇 줄이 들어갈지는 실측한 높이로 조판기가 정한다.
# 쪽당 개수를 고정하면 글 길이 편차를 못 이겨 넘치거나 남는다
PER = {'cards': 2, 'dtable': 1, 'ts': 1, 'parts': 2, 'feats': 2, 'press': 2}
SHOT_PER = {'pfwide': 4, 'pfphone': 3}


def det(html, brand):
    return '<div class="det" style="--brand:%s">%s</div>' % (brand, html)


def sec_head(step, title, lead, rline=''):
    """장 안의 절 머리. 제목은 왼쪽, 리드는 오른쪽에 두어 지면 폭을 쓴다."""
    right = ''
    if rline:
        right += '<div class="rline">%s</div>' % rline
    if lead:
        right += '<p class="lead">%s</p>' % lead
    return ('<div class="sechd"><div><div class="step">%s</div>'
            '<h2 class="stitle">%s</h2></div><div class="sectxt">%s</div></div>'
            % (step, title, right))


def grid(kind, items, brand):
    """사이트 컴포넌트를 쪽 단위 격자로 다시 그린다."""
    return det('<div class="%s pg%s">%s</div>' % (kind, kind, ''.join(items)), brand)


def chunk(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def figure_page(b, brand, tag):
    return Block(det('<div class="figure pgfigure"><img src="%s" alt="">'
                     '<div class="cap">%s</div></div>' % (b['src'], b['cap']), brand),
                 newpage=True, tag=tag)


def section_pages(sec, brand, tag):
    """절 하나를 쪽들로 짠다. 머리는 첫 쪽 위에 붙는다."""
    out = []
    head = sec_head(sec['step'], sec['title'], sec['lead'], sec['rline'])
    pending_head = det(head, brand)

    def emit(html, newpage=False):
        nonlocal pending_head
        if pending_head:
            # 절 머리는 앞 쪽이 어느 정도 찼을 때만 새 쪽으로 넘긴다.
            # 절마다 새 쪽을 강제하면 반쯤 빈 쪽이 줄줄이 생긴다
            out.append(Block(pending_head, softpage=True, keepnext=True, tag=tag))
            pending_head = None
            newpage = False
        out.append(Block(html, newpage=newpage, tag=tag))

    for b in sec['blocks']:
        t = b['t']
        if t == 'figure':
            emit(det('<div class="figure pgfigure"><img src="%s" alt="">'
                     '<div class="cap">%s</div></div>' % (b['src'], b['cap']), brand))
        elif t in PER:
            parts = chunk(b['items'], PER[t])
            for part in parts:
                emit(grid(t, part, brand))
        elif t == 'ov':
            emit(det(b['html'], brand), newpage=False)
        elif t in ('prose', 'raw'):
            emit(det(b['html'], brand), newpage=False)
        elif t == 'docs':
            pass
    if pending_head:
        out.append(Block(pending_head, softpage=True, tag=tag))
    return out


def shot_pages(kind, shots, brand, tag, title='실제 화면'):
    """화면 사진을 쪽마다 같은 수로 깔고 캡션을 붙인다."""
    out = []
    per = SHOT_PER[kind]
    for n, part in enumerate(chunk(shots, per)):
        cells = ''.join(
            '<figure class="pf"><img src="assets/image/%s" alt="%s">'
            '<figcaption>%s</figcaption></figure>' % (f, c, c) for f, c in part)
        head = ('<h3 class="pgh">%s</h3>' % title) if n == 0 else ''
        out.append(Block('%s<div class="pfgrid %s">%s</div>' % (head, kind, cells),
                         softpage=(n == 0), keepnext=(n == 0), tag=tag))
    return out
