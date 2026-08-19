# -*- coding: utf-8 -*-
"""포트폴리오 지면을 짠다.

쪽마다 담을 개수를 못 박으면 글 길이 편차 때문에 어떤 쪽은 텅 비고 어떤
쪽은 넘친다. 그래서 격자는 한 줄씩 내고, 한 쪽에 몇 줄이 들어갈지는
실측한 높이로 조판기가 정한다. 대신 쪽마다 절 이름을 얹어 흘러가는 문서가
아니라 한 판으로 읽히게 한다.
"""
import re

from pdfkit import Block

# 격자 한 줄에 들어가는 개수. 한 줄에 적게 담으면 줄이 늘어나 마지막 쪽이
# 어중간하게 남는다. 세 칸으로 조여 절 하나가 되도록 한 쪽에 들어가게 한다.
# 표(dtable)는 통째로 한 덩어리다 — 줄마다 쪼개면 조판기가 줄 사이를 벌려
# 항목마다 아래에 빈 자리가 생긴다
PER = {'cards': 3, 'dtable': 99, 'ts': 1, 'parts': 3, 'feats': 3, 'press': 3}

# 화면은 자르지 않는다. 그래서 한 쪽에 몇 장인지는 사진 비율이 정한다.
# 넓은 화면(1.9:1)은 지면 폭을 다 써야 읽히므로 한 쪽에 한 장,
# 세로로 긴 폰 화면은 세 장이 나란히 서야 지면이 찬다
SHOT_PER = {'pfwide': 1, 'pfphone': 3}


def chunk(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def spread(seq, per):
    """한 줄에 per개까지 담되 줄마다 고르게 나눈다.

    앞에서부터 꽉 채우면 7개를 3칸에 담을 때 3·3·1 이 되어 마지막 줄에
    카드 한 장만 덩그러니 남는다. 3·2·2 로 나누면 그럴 일이 없다.
    """
    n = len(seq)
    if n <= per:
        return [seq]
    rows = -(-n // per)
    base, extra = divmod(n, rows)
    out, i = [], 0
    for r in range(rows):
        k = base + (1 if r < extra else 0)
        out.append(seq[i:i + k])
        i += k
    return out


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


def linebreak(html, fn):
    """카드 본문만 골라 줄바꿈 규칙을 먹인다.

    카드 전체에 걸면 라벨·제목까지 잘리므로 <p> 와 <li> 안쪽만 손댄다.
    태그별로 따로 훑는다 — 역참조를 쓰면 편집 과정에서 쉽게 깨진다.
    """
    for tag in ('p', 'li'):
        pat = re.compile(r'(<%s[ >][^>]*>|<%s>)(.*?)(</%s>)' % (tag, tag, tag), re.S)
        html = pat.sub(lambda m: m.group(1) + fn(m.group(2)) + m.group(3), html)
    return html


def section_pages(sec, brand, tag, grp='', brk=None, budget=0):
    """절 하나를 블록으로 낸다. 머리는 첫 쪽에, 이어지는 쪽에는 조판기가 얹는다.

    같은 grp 를 달아 두면 조판기가 절 전체를 한 쪽에 넣을 수 있는지 먼저 보고,
    들어가면 통째로 넘긴다. 절 머리와 앞부분만 앞 쪽 바닥에 걸치는 일이 없다.
    """
    out = []
    head = det(sec_head(sec['step'], sec['title'], sec['lead'], sec['rline']), brand)
    run = (sec['step'], sec['title'])
    pending = head

    def emit(html):
        nonlocal pending
        if pending:
            out.append(Block(pending, softpage=True, keepnext=True, tag=tag, head=run, grp=grp))
            pending = None
        out.append(Block(html, tag=tag, head=run, grp=grp))

    # 'docs' 는 사이트의 문서 보기 버튼이라 지면에 아무것도 내지 않는다.
    # 세지 않아야 "도식 하나뿐인 절" 판정이 맞는다
    blocks = [b for b in sec['blocks'] if b['t'] != 'docs']
    # 절의 첫 덩어리가 도식이면 머리와 한 블록으로 묶는다.
    # 도식은 대개 한 쪽을 통째로 먹어서, 따로 두면 머리만 있는 빈 쪽이 앞에 생긴다
    if blocks and blocks[0]['t'] == 'figure' and budget:
        b = blocks[0]
        out.append(Block(
            '<div class="det fillblk figpage" style="--brand:%s">%s'
            '<div class="figure pgfigure"><img src="%s" alt="">'
            '<div class="cap">%s</div></div></div>'
            % (brand, sec_head(sec['step'], sec['title'], sec['lead'], sec['rline']),
               b['src'], b['cap']),
            newpage=True, tag=tag, head=run, fixh=budget, grp=grp))
        pending = None
        blocks = blocks[1:]

    for b in blocks:
        t = b['t']
        if t == 'figure':
            emit(det('<div class="figure pgfigure"><img src="%s" alt="">'
                     '<div class="cap">%s</div></div>' % (b['src'], b['cap']), brand))
        elif t in PER:
            for part in spread(b['items'], PER[t]):
                body = ''.join(part)
                if brk:
                    # 카드 본문은 줄 끝이 늘 쉼표나 마침표가 되게 조각으로 묶는다
                    body = linebreak(body, brk)
                # 칸 수를 줄에 담긴 개수에 맞춘다. 3칸 격자에 2개만 놓으면
                # 오른쪽 한 칸이 사라진 것처럼 보인다
                cols = ' style="grid-template-columns:repeat(%d,1fr)"' % len(part)                     if len(part) < PER[t] else ''
                emit(det('<div class="%s pg%s"%s>%s</div>' % (t, t, cols, body), brand))
        elif t in ('ov', 'prose', 'raw'):
            emit(det(b['html'], brand))
    if pending:
        out.append(Block(pending, softpage=True, tag=tag, head=run, grp=grp))
    return out


TEXT_W = 994      # 지면 좌우 여백을 뺀 본문 폭
SHOT_GAP = 14     # 화면 사이 간격
SHOT_PAD = 44     # 화면을 감싼 면의 좌우 여백 합
SHOT_CHROME = 66  # 면 위쪽 여백 + 설명줄이 먹는 높이
SEC_HEAD_H = 108  # 절 머리가 먹는 높이


def fit(nat, maxw, maxh):
    """자르지 않고 들어가는 크기를 낸다. 비율은 건드리지 않는다."""
    w, h = nat
    s = min(maxw / float(w), maxh / float(h))
    return int(w * s), int(h * s)


def shot_pages(kind, shots, brand, tag, budget, dims):
    """화면은 크게 싣는다. 포트폴리오에서 화면이 주인공이다.

    한 쪽을 통째로 쓰는 블록으로 낸다. 절 머리는 첫 블록 안에 넣는다.
    따로 떼면 "실제 화면" 넉 자만 있는 빈 쪽이 생긴다.

    감싸는 면은 사진 크기에 맞춰 짠다. 면을 지면만큼 벌려 놓고 사진을
    가운데 두면 회색 여백이 남는데, 그건 여백이 아니라 빈자리다.
    """
    out = []
    run = ('SCREENS', '실제 화면')
    head = sec_head('SCREENS', '실제 화면', '', '')
    per = SHOT_PER[kind]
    maxw = (TEXT_W - SHOT_GAP * (per - 1)) / float(per) - SHOT_PAD
    for n, part in enumerate(chunk(shots, per)):
        maxh = budget - (SEC_HEAD_H if n == 0 else 0) - SHOT_CHROME
        cells = ''
        for f, c in part:
            w, _ = fit(dims[f], maxw, maxh)
            cells += ('<figure class="pf" style="width:%dpx">'
                      '<img src="assets/image/%s" alt="%s">'
                      '<figcaption>%s</figcaption></figure>' % (w + SHOT_PAD, f, c, c))
        grid = '<div class="pfgrid %s">%s</div>' % (kind, cells)
        html = ('<div class="det fillblk" style="--brand:%s">%s%s</div>'
                % (brand, head if n == 0 else '', grid))
        out.append(Block(html, newpage=True, tag=tag, head=run, fixh=budget))
    return out
