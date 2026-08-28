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
    # 절 번호를 큰 고스트 숫자로 왼쪽에 세운다. 절 시작 쪽은 아래가 비기 쉬운데,
    # 이 숫자가 기둥이 되어 남은 자리가 미완성이 아니라 여백으로 읽힌다
    mm = re.match(r'\s*(\d+)', re.sub(r'<[^>]+>', '', step))
    ghost = '<div class="secno">%s</div>' % mm.group(1) if mm else ''
    return ('<div class="sechd">%s<div><div class="step">%s</div>'
            '<h2 class="stitle">%s</h2></div><div class="sectxt">%s</div></div>'
            % (ghost, step, title, right))


def linebreak(html, fn):
    """카드 본문만 골라 줄바꿈 규칙을 먹인다.

    카드 전체에 걸면 라벨·제목까지 잘리므로 <p> 와 <li> 안쪽만 손댄다.
    태그별로 따로 훑는다 — 역참조를 쓰면 편집 과정에서 쉽게 깨진다.
    """
    for tag in ('p', 'li'):
        pat = re.compile(r'(<%s[ >][^>]*>|<%s>)(.*?)(</%s>)' % (tag, tag, tag), re.S)
        html = pat.sub(lambda m: m.group(1) + fn(m.group(2)) + m.group(3), html)
    return html


def _grab(s, i, tag='div'):
    """i 위치에서 시작하는 tag 요소 하나를 통째로 떼어 낸다."""
    depth = 0
    pat = re.compile('</?' + tag + r'\b[^>]*>')
    j = i
    while True:
        m = pat.search(s, j)
        if not m:
            return s[i:]
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return s[i:m.end()]
        else:
            depth += 1
        j = m.end()


def ev_split(html):
    """`.ev` 묶음을 evbox 하나씩으로 쪼갠다.

    한 묶음을 한 블록으로 두면 그래프 하나에 표 둘이 든 상자가 한 쪽을 넘는다.
    조판기가 쪼갤 수 없으니 축소해서 담는데, 그래프는 SVG 라 폭을 늘리면 높이도
    같이 늘어 축소가 상쇄된다. 그래서 미리 쪼개 둔다.

    그래프가 든 상자는 다시 「제목+그래프」와 「나머지」로 나눈다.
    """
    if 'class="ev' not in html[:60]:
        return [html]
    out = []
    i = html.find('<div class="evbox')
    while i >= 0:
        box = _grab(html, i)
        out += _box_split(box)
        i = html.find('<div class="evbox', i + len(box))
    return out or [html]


def _children(inner):
    """상자 안 최상위 조각들을 순서대로 돌려준다."""
    out, i, n = [], 0, len(inner)
    while i < n:
        if inner[i] != '<':
            j = inner.find('<', i)
            j = n if j < 0 else j
            if inner[i:j].strip():
                out.append(inner[i:j])
            i = j
            continue
        m = re.match(r'<([a-zA-Z0-9]+)', inner[i:])
        if not m:
            break
        tag = m.group(1)
        if tag in ('br', 'img', 'hr', 'input'):
            j = inner.index('>', i) + 1
            out.append(inner[i:j])
            i = j
            continue
        el = _grab(inner, i, tag)
        out.append(el)
        i += len(el)
    return out


def _box_split(box, per=2):
    """evbox 하나를 지면에 담을 만한 크기로 자른다.

    그래프(SVG)는 폭을 늘리면 높이도 같이 늘어 축소가 듣지 않는다. 그래서 먼저 떼어 낸다.
    남은 조각은 표나 목록 앞에서 끊는다 — 표 한가운데가 갈리지 않는다.
    앞 조각에 아직 내용이 없으면 끊지 않는다. 제목만 있는 쪽이 생기면 안 된다.
    """
    open_end = box.index('>') + 1
    open_tag = box[:open_end]
    inner = box[open_end:box.rindex('</div>')]
    close = '</div>'

    m = re.search(r'<h3>(.*?)</h3>', inner)
    title = m.group(0) if m else ''
    name = re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''
    rest = inner[m.end():] if m else inner
    rest = re.sub(r'<!--\s*(?:cumul|trend):(?:begin|end)\s*-->', '', rest)

    kids = _children(rest)
    groups, cur, filled = [], [], False
    for el in kids:
        heavy = el.lstrip().startswith('<svg') or el.lstrip().startswith('<table')             or 'class="tsrows' in el[:40]
        if heavy and filled:
            groups.append(cur)
            cur, filled = [], False
        cur.append(el)
        if el.strip():
            filled = True
        if el.lstrip().startswith('<svg'):
            groups.append(cur)
            cur, filled = [], False
    if cur:
        groups.append(cur)
    groups = [g for g in groups if ''.join(g).strip()]
    if not groups:
        return ['<div class="ev">' + open_tag + inner + close + '</div>']

    parts = []
    for k, g in enumerate(groups):
        if k == 0:
            head = title
        elif k == 1 and name:
            # 이어지는 첫 조각에만 꼬리표를 단다. 셋 이상이면 같은 제목이 되풀이돼 어수선하다
            head = '<h3>%s <span class="cont">이어서</span></h3>' % name
        else:
            head = ''
        parts.append('<div class="ev">' + open_tag + head + ''.join(g) + close + '</div>')
    return parts


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
    # 도식은 대개 한 쪽을 통째로 먹어서, 따로 두면 머리만 있는 빈 쪽이 앞에 생긴다.
    #
    # 다만 뒤에 다른 덩어리가 더 있으면 통째로 먹여선 안 된다.
    # 언론 보도 절이 그랬다 — 사진이 한 쪽을 다 쓰고 기사 카드 둘만 다음 쪽에 남아
    # 아래가 640px 비었다. 뒤에 내용이 있으면 사진 높이를 눌러 한 쪽에 같이 앉힌다
    # 뒤에 덩어리가 둘 이하로 남으면 사진과 함께 한 블록으로 묶는다.
    # 따로 두면 사진이 한 쪽을 다 먹고 남은 것만 다음 쪽에 실려 아래가 텅 빈다.
    # 묶으면 조판기가 쪼갤 수 없으니 한 쪽에 같이 앉는다
    if (blocks and blocks[0]['t'] == 'figure' and budget
            and 1 < len(blocks) <= 3 and all(b['t'] in PER for b in blocks[1:])):
        b = blocks[0]
        tail = ''
        for x in blocks[1:]:
            body = ''.join(x['items'])
            if brk:
                body = linebreak(body, brk)
            tail += '<div class="%s pg%s">%s</div>' % (x['t'], x['t'], body)
        out.append(Block(
            '<div class="det fillblk figpage" style="--brand:%s">%s'
            '<div class="figure pgfigure figshort"><img src="%s" alt="">'
            '<div class="cap">%s</div></div>%s</div>'
            % (brand, sec_head(sec['step'], sec['title'], sec['lead'], sec['rline']),
               b['src'], b['cap'], tail),
            newpage=True, tag=tag, head=run, fixh=budget, grp=grp))
        pending = None
        blocks = []
    elif blocks and blocks[0]['t'] == 'figure' and budget:
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
                # 칸 수를 줄에 담긴 개수에 맞춘다. CSS 가 !important 라
                # 변수로 넘겨야 먹는다
                cols = (' style="--cols:%d"' % len(part)) if len(part) < PER[t] else ''
                emit(det('<div class="%s pg%s"%s>%s</div>' % (t, t, cols, body), brand))
        elif t in ('ov', 'prose', 'raw'):
            # `.ev` 묶음은 상자 하나씩 낸다. 통째로 두면 한 쪽을 넘긴다
            for piece in ev_split(b['html']):
                emit(det(piece, brand))
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
