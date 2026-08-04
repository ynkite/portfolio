# -*- coding: utf-8 -*-
"""갤러리에 넣을 화면 사진을 다듬는 공용 도구.

- trim_border  : 네 변에 둘린 균일한 테두리(모달 뒤 어두운 막, 여백)를 걷어 낸다
- corner_radius: 코너에 박힌 라운드 크기를 재어 온다
- round_corners: 라운드를 알파로 깎아 카드 배경 위에 깔끔하게 얹는다
- save          : PNG로 저장하고 너무 크면 JPEG로 다시 저장한다
"""
import os
from PIL import Image, ImageDraw

MAXKB = 500     # 이보다 크면 사진에 가까운 화면이라 보고 JPEG로 바꾼다


def _band(px, pts):
    n = len(pts)
    s = [0, 0, 0]
    for x, y in pts:
        c = px[x, y]
        s[0] += c[0]
        s[1] += c[1]
        s[2] += c[2]
    return (s[0] / n, s[1] / n, s[2] / n)


def _near(a, b, tol):
    return sum(abs(a[i] - b[i]) for i in range(3)) <= tol


def trim_border(im, tol=26, keep=120):
    """코너 색과 같은 테두리를 네 변에서 걷어 낸다.

    모달 캡처는 뒤에 깔린 어두운 막이 테두리로 남는다. 그 막만 벗겨야
    모달 자체가 온전히 남는다. keep보다 작아지면 멈춘다.
    """
    px = im.load()
    w, h = im.size
    x0, y0, x1, y1 = 0, 0, w, h
    ref = px[0, 0]
    for _ in range(max(w, h)):
        cx = list(range(x0 + (x1 - x0) // 5, x0 + (x1 - x0) * 4 // 5, 2))
        cy = list(range(y0 + (y1 - y0) // 5, y0 + (y1 - y0) * 4 // 5, 2))
        moved = False
        if y1 - y0 > keep and _near(_band(px, [(x, y0) for x in cx]), ref, tol):
            y0 += 1
            moved = True
        if y1 - y0 > keep and _near(_band(px, [(x, y1 - 1) for x in cx]), ref, tol):
            y1 -= 1
            moved = True
        if x1 - x0 > keep and _near(_band(px, [(x0, y) for y in cy]), ref, tol):
            x0 += 1
            moved = True
        if x1 - x0 > keep and _near(_band(px, [(x1 - 1, y) for y in cy]), ref, tol):
            x1 -= 1
            moved = True
        if not moved:
            break
    return im.crop((x0, y0, x1, y1))


def trim_white(im, thr=249, frac=.985):
    """네 변에서 거의 흰 줄만 걷어 낸다. 붙여 넣은 캔버스 여백을 없애는 용도다."""
    px = im.load()
    w, h = im.size
    x0, y0, x1, y1 = 0, 0, w, h

    def wr(y, a, b):
        n = list(range(a, b, 2))
        return sum(1 for x in n if min(px[x, y][:3]) >= thr) / float(len(n))

    def wc(x, a, b):
        n = list(range(a, b, 2))
        return sum(1 for y in n if min(px[x, y][:3]) >= thr) / float(len(n))

    while y1 - y0 > 60 and wr(y0, x0, x1) >= frac:
        y0 += 1
    while y1 - y0 > 60 and wr(y1 - 1, x0, x1) >= frac:
        y1 -= 1
    while x1 - x0 > 60 and wc(x0, y0, y1) >= frac:
        x0 += 1
    while x1 - x0 > 60 and wc(x1 - 1, y0, y1) >= frac:
        x1 -= 1
    return im.crop((x0, y0, x1, y1))


def _lum(c):
    return (c[0] * 299 + c[1] * 587 + c[2] * 114) / 1000.0


def card_box(im, floor=150, frac=.5):
    """어두운 막 위에 떠 있는 카드(모달)의 사각형을 찾는다.

    막이 반투명이라 색이 고르지 않다. 그래서 테두리 색을 좇는 대신
    '어둡지 않은 픽셀이 몰려 있는 줄'을 카드로 본다. 카드 안에는 흰
    입력창뿐 아니라 그라데이션 버튼도 있어서 '밝다'로 재면 끊긴다.
    """
    px = im.load()
    w, h = im.size
    rows = [sum(1 for x in range(0, w, 2) if _lum(px[x, y]) >= floor) / float(len(range(0, w, 2)))
            for y in range(h)]
    cols = [sum(1 for y in range(0, h, 2) if _lum(px[x, y]) >= floor) / float(len(range(0, h, 2)))
            for x in range(w)]
    def longest(vals, gap=8):
        """가장 길게 이어진 구간을 고른다.

        처음과 끝만 보면 카드 밖의 밝은 데까지 삼킨다. 반대로 입력창
        테두리 같은 한 줄 경계에 구간이 끊기므로 짧은 끊김은 이어 붙인다.
        """
        best = (0, 0)
        s, blanks = None, 0
        for i, v in enumerate(vals + [0.0] * (gap + 1)):
            if v >= frac:
                if s is None:
                    s = i
                blanks = 0
            elif s is not None:
                blanks += 1
                if blanks > gap:
                    e = i - blanks
                    if e - s > best[1] - best[0]:
                        best = (s, e)
                    s = None
        return best

    y0, y1 = longest(rows)
    x0, x1 = longest(cols)
    if y1 <= y0 or x1 <= x0:
        return (0, 0, w, h)
    return (x0, y0, x1, y1)


def white_radius(im, floor=150, limit=60):
    """코너에서 카드가 시작되기까지의 거리 — 라운드 반지름과 같다."""
    px = im.load()
    w, h = im.size
    out = 0
    for cx, sx in ((0, 1), (w - 1, -1)):
        for cy in (0, h - 1):
            k = 0
            while k < limit and _lum(px[cx + sx * k, cy]) < floor:
                k += 1
            out = max(out, k)
    return out


def corner_radius(im, tol=30, limit=90):
    """네 코너에 남은 배경이 어디까지 파고들었는지 재어 최대값을 돌려준다."""
    px = im.load()
    w, h = im.size
    out = 0
    for cx, cy, sx in ((0, 0, 1), (w - 1, 0, -1), (0, h - 1, 1), (w - 1, h - 1, -1)):
        ref = px[cx, cy]
        k = 0
        while k < limit and _near(px[cx + sx * k, cy], ref, tol):
            k += 1
        out = max(out, k)
    return out


def round_corners(im, r):
    """라운드 바깥을 투명하게 만든다."""
    w, h = im.size
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    im = im.convert('RGBA')
    im.putalpha(mask)
    return im


def save(im, path_noext, width=None, maxkb=MAXKB):
    """가로 폭을 맞춰 저장한다. 확대는 하지 않는다 — 없는 화질은 만들어지지 않는다."""
    if width and im.width > width:
        im = im.resize((width, int(round(im.height * width / float(im.width)))),
                       Image.LANCZOS)
    png = path_noext + '.png'
    im.save(png, optimize=True)
    size = os.path.getsize(png)
    if size > maxkb * 1024 and im.mode != 'RGBA':
        os.remove(png)
        out = path_noext + '.jpg'
        im.save(out, quality=88, optimize=True, progressive=True)
    else:
        out = png
    print('  %-28s %dx%d  %dKB' % (os.path.basename(out), im.width, im.height,
                                   os.path.getsize(out) // 1024))
    return out
