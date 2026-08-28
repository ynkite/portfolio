# -*- coding: utf-8 -*-
"""캡처에 딸려 온 스크롤바를 찾고 지운다.

스크롤바는 좁은 세로 띠다. 띠 안쪽 색이 세로로 거의 일정하고, 좌우 이웃과
뚜렷하게 다르며, 화면 높이의 상당 부분을 차지한다. 그 세 가지로 찾는다.

사용
  python tools/scrollbar.py            찾기만 한다
  python tools/scrollbar.py --fix      찾은 자리를 왼쪽 배경색으로 메운다
"""
import os
import shutil
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMGDIR = os.path.join(ROOT, 'assets', 'image')
BAK = os.path.join(ROOT, 'tools', '_backup', '2026-08-19-scrollbar')

MINW, MAXW = 5, 22          # 스크롤바 폭
MIN_RUN = 0.25              # 세로로 이만큼은 이어져야 한다
EDGE = 14                   # 좌우 이웃과 이만큼은 달라야 한다


def profile(im):
    """열마다 밝기 중앙값을 낸다.

    스크롤바에는 어두운 손잡이가 있어 세로 편차가 크다. 평균·편차로 거르면
    아는 사례도 못 잡는다. 중앙값이라야 트랙 색이 그대로 남는다.
    """
    w, h = im.size
    ys = list(range(int(h * .12), int(h * .95), max(1, h // 300)))
    px = im.load()
    out = []
    for x in range(w):
        v = sorted(sum(px[x, y]) / 3.0 for y in ys)
        out.append(v[len(v) // 2])
    return out


def find(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    med = profile(im)
    hits = []
    x = 1
    while x < w - 1:
        # 왼쪽 이웃과 뚜렷이 달라지는 지점에서 띠를 연다
        if abs(med[x] - med[x - 1]) < EDGE:
            x += 1
            continue
        base = med[x - 1]
        e = x
        while e < w - 1 and abs(med[e] - base) >= EDGE and abs(med[e] - med[x]) < EDGE:
            e += 1
        width = e - x
        if MINW <= width <= MAXW and e < w - 1:
            right = med[e]
            inner = med[x]
            # 띠 양옆이 서로 비슷해야 한다 — 같은 배경 위에 얹힌 띠
            if abs(inner - right) >= EDGE and abs(base - right) <= 34:
                hits.append((x, e - 1, round(inner), round(base), round(right)))
        x = max(e, x + 1)
    return im, hits


def fix(path, band):
    x0, x1 = band
    im = Image.open(path).convert('RGBA')
    px = im.load()
    w, h = im.size
    ref_x = max(0, x0 - 3)
    n = 0
    for y in range(h):
        for x in range(x0, x1 + 1):
            px[x, y] = px[ref_x, y]
        n += 1
    im.save(path)
    return n


def main():
    do_fix = '--fix' in sys.argv
    os.makedirs(BAK, exist_ok=True)
    names = sorted(f for f in os.listdir(IMGDIR)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg')))
    total = 0
    for f in names:
        p = os.path.join(IMGDIR, f)
        im, hits = find(p)
        if not hits:
            continue
        total += len(hits)
        print('%-30s %4dx%-4d %s' % (f, im.size[0], im.size[1],
                                     ' '.join('x%d~%d(%d|%d,%d)' % hh for hh in hits)))
        if do_fix:
            b = os.path.join(BAK, f)
            if not os.path.exists(b):
                shutil.copy2(p, b)
            for x0, x1, _, _, _ in hits:
                fix(p, (x0, x1))
            print('   -> 지움')
    print('의심 띠 %d개 / 사진 %d장' % (total, len(names)))


if __name__ == '__main__':
    main()
