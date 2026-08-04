# -*- coding: utf-8 -*-
"""그림판에서 여러 화면을 흰 캔버스에 붙여 만든 합성 이미지를 화면별로 되쪼갠다.

원본 픽셀을 그대로 잘라 내기만 하므로 화질 손실이 없다. numpy 없이 PIL만 쓴다.
사용 — python tools/split_panels.py <이미지> <출력폴더> <접두어>
"""
import os
import sys
from PIL import Image

DOWN = 4        # 탐지용 축소 배율. 얇은 흰 틈까지 살리려면 8은 너무 거칠다
WHITE = 248     # 이 값 이상이면 배경(흰색)으로 본다
RATIO = 0.993   # 한 줄에서 배경 픽셀이 이 비율을 넘으면 '빈 줄'로 본다.
                # 붙어 있는 패널 사이의 1~2px 틈에 잡티가 섞여도 견딘다
MIN_SIDE = 120  # 이보다 작은 조각은 잡티로 버린다


def _content_map(im):
    """축소한 흑백 이미지에서 '내용이 있는' 픽셀 좌표 집합을 만든다."""
    g = im.convert('L').resize((im.width // DOWN or 1, im.height // DOWN or 1), Image.BOX)
    px = g.load()
    w, h = g.size
    rows = [sum(1 for x in range(w) if px[x, y] >= WHITE) / w <= RATIO for y in range(h)]
    cols = [sum(1 for y in range(h) if px[x, y] >= WHITE) / h <= RATIO for x in range(w)]
    return rows, cols, w, h


def _bands(flags, gap=1):
    """True가 이어지는 구간을 [(start, end)]로 묶는다. gap 이하의 끊김은 이어 붙인다."""
    out, s = [], None
    blanks = 0
    for i, v in enumerate(flags):
        if v:
            if s is None:
                s = i
            blanks = 0
        elif s is not None:
            blanks += 1
            if blanks > gap:
                out.append((s, i - blanks))
                s = None
    if s is not None:
        out.append((s, len(flags) - 1))
    return out


def _tighten(im, box):
    """자른 영역의 흰 여백을 한 번 더 깎아 낸다."""
    x0, y0, x1, y1 = box
    g = im.crop(box).convert('L')
    px = g.load()
    w, h = g.size
    top = next((y for y in range(h) if any(px[x, y] < WHITE for x in range(w))), 0)
    bot = next((y for y in range(h - 1, -1, -1) if any(px[x, y] < WHITE for x in range(w))), h - 1)
    lft = next((x for x in range(w) if any(px[x, y] < WHITE for y in range(h))), 0)
    rgt = next((x for x in range(w - 1, -1, -1) if any(px[x, y] < WHITE for y in range(h))), w - 1)
    return (x0 + lft, y0 + top, x0 + rgt + 1, y0 + bot + 1)


def split(path, outdir, prefix):
    im = Image.open(path)
    if im.mode in ('RGBA', 'LA', 'P'):
        # 투명 배경은 흰색으로 깔아야 배경 판정이 맞는다
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA')
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')

    rows, cols, _, _ = _content_map(im)
    os.makedirs(outdir, exist_ok=True)
    n = 0
    # 가로 띠를 먼저 나누고, 띠 안에서 다시 세로로 나눈다 (그림판 배치가 보통 이 형태다)
    for ry0, ry1 in _bands(rows):
        y0, y1 = ry0 * DOWN, min((ry1 + 1) * DOWN, im.height)
        strip = im.crop((0, y0, im.width, y1))
        srows, scols, _, _ = _content_map(strip)
        for cx0, cx1 in _bands(scols):
            x0, x1 = cx0 * DOWN, min((cx1 + 1) * DOWN, im.width)
            box = _tighten(im, (x0, y0, x1, y1))
            if box[2] - box[0] < MIN_SIDE or box[3] - box[1] < MIN_SIDE:
                continue
            n += 1
            out = os.path.join(outdir, '%s-%02d.png' % (prefix, n))
            im.crop(box).save(out, optimize=True)
            print('  %s  %dx%d' % (os.path.basename(out), box[2] - box[0], box[3] - box[1]))
    print('%s → %d개' % (os.path.basename(path), n))
    return n


if __name__ == '__main__':
    split(sys.argv[1], sys.argv[2], sys.argv[3])
