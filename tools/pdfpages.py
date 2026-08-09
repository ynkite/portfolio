# -*- coding: utf-8 -*-
"""포트폴리오 지면을 짠다.

쪽마다 담을 개수를 못 박으면 글 길이 편차 때문에 어떤 쪽은 텅 비고 어떤
쪽은 넘친다. 그래서 격자는 한 줄씩 내고, 한 쪽에 몇 줄이 들어갈지는
실측한 높이로 조판기가 정한다. 대신 쪽마다 절 이름을 얹어 흘러가는 문서가
아니라 한 판으로 읽히게 한다.
"""
from pdfkit import Block

# 격자 한 줄에 들어가는 개수
PER = {'cards': 2, 'dtable': 1, 'ts': 1, 'parts': 2, 'feats': 2, 'press': 2}
SHOT_PER = {'pfwide': 2, 'pfphone': 3}


def chunk(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def det(html, brand):
    return '<div class="det" style="--brand:%s">%s</div>' % (brand, html)


def sec_head(step, title, lead, rline=''):
    """절 첫 쪽의 머리. 제목은 왼쪽, 리드는 오른쪽에 두어 지면 폭을 쓴다."""
    right = ''
    if rline:
        right += '<div class="rline">%s</div>' % rline
    if lead:
        right += '<p class="lead">%s</p>' % lead
    return ('<div class="sechd"><div><div class="step">%s</div>'
            '<h2 class="stitle">%s</h2></div><div class="sectxt">%s</div></div>'
            % (step, title, right))


def section_pages(sec, brand, tag):
    """절 하나를 블록으로 낸다. 머리는 첫 쪽에, 이어지는 쪽에는 조판기가 얹는다."""
    out = []
    head = det(sec_head(sec['step'], sec['title'], sec['lead'], sec['rline']), brand)
    run = (sec['step'], sec['title'])
    pending = head

    def emit(html):
        nonlocal pending
        if pending:
            out.append(Block(pending, softpage=True, keepnext=True, tag=tag, head=run))
            pending = None
        out.append(Block(html, tag=tag, head=run))

    for b in sec['blocks']:
        t = b['t']
        if t == 'figure':
            emit(det('<div class="figure pgfigure"><img src="%s" alt="">'
                     '<div class="cap">%s</div></div>' % (b['src'], b['cap']), brand))
        elif t in PER:
            for part in chunk(b['items'], PER[t]):
                emit(det('<div class="%s pg%s">%s</div>' % (t, t, ''.join(part)), brand))
        elif t in ('ov', 'prose', 'raw'):
            emit(det(b['html'], brand))
    if pending:
        out.append(Block(pending, softpage=True, tag=tag, head=run))
    return out


def shot_pages(kind, shots, brand, tag):
    """화면은 크게 싣는다. 포트폴리오에서 화면이 주인공이다."""
    out = []
    run = ('SCREENS', '실제 화면')
    head = det(sec_head('SCREENS', '실제 화면', '', ''), brand)
    for n, part in enumerate(chunk(shots, SHOT_PER[kind])):
        cells = ''.join(
            '<figure class="pf"><img src="assets/image/%s" alt="%s">'
            '<figcaption>%s</figcaption></figure>' % (f, c, c) for f, c in part)
        body = det('<div class="pfgrid %s">%s</div>' % (kind, cells), brand)
        if n == 0:
            out.append(Block(head, softpage=True, keepnext=True, tag=tag, head=run))
        out.append(Block(body, tag=tag, head=run))
    return out
