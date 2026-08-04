# -*- coding: utf-8 -*-
"""폰 목업 캡처를 잘라내지 않고 같은 크기로 맞춘다.

캡처마다 브라우저 창 높이가 달라 비율이 1.51 ~ 2.04까지 벌어져 있다.
잘라 맞추면 화면이 잘리고, 여백을 대면 카드 안에 흰 띠가 남는다.
그래서 배경만 있는 줄 — 바로 윗줄과 거의 같은 줄 — 을 찾아
그 줄만 늘리거나 지워 목표 비율을 만든다. 내용은 한 픽셀도 잃지 않는다.

마지막에 목업 라운드를 알파로 깎아 카드 배경 위에 깔끔하게 얹는다.

사용 — python tools/phone_norm.py <입력> <출력> [목표가로 목표세로]
"""
import sys
from PIL import Image, ImageDraw

TW, TH = 428, 882    # 그림자를 걷어 내면 11장이 모두 이 크기다. 확대 없이 원본 그대로 쓴다
FLAT = 2.0           # 이 값 아래면 '윗줄과 같은 줄'로 본다
MINRUN = 12          # 이만큼 이어진 평평한 구간에서만 손댄다
EDGE = 3             # 구간 양 끝은 경계라 건드리지 않는다
RADIUS = 30          # 목업에 박힌 라운드(27px)보다 살짝 크게 깎아 코너를 깔끔하게 만든다


STEP = 14   # 이만큼 한 픽셀에 튀면 목업 경계로 본다


def _rough_box(im, tol=45):
    """배경(x 방향으로 색이 같은 세로 그라데이션)에서 벗어나는 영역을 크게 잡는다."""
    px = im.load()
    w, h = im.size
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        b = px[0, y]
        for x in range(w):
            p = px[x, y]
            if abs(p[0] - b[0]) + abs(p[1] - b[1]) + abs(p[2] - b[2]) > tol:
                x0 = min(x0, x)
                x1 = max(x1, x)
                y0 = min(y0, y)
                y1 = max(y1, y)
    return None if x1 < 0 else (x0, y0, x1 + 1, y1 + 1)


def _edge(prof, forward):
    """밝기 프로파일에서 계단처럼 꺾이는 첫 지점을 찾는다.

    목업 경계는 한 픽셀에서 확 바뀌고, 그림자는 완만하게 변한다.
    그래서 바깥에서부터 훑어 처음으로 크게 튀는 곳이 목업의 끝이다.
    """
    n = len(prof)
    rng = range(n - 1) if forward else range(n - 1, 0, -1)
    for i in rng:
        j = i + 1 if forward else i - 1
        if abs(prof[j] - prof[i]) >= STEP:
            return j
    return 0 if forward else n - 1


def trim_mockup(im, tol=45):
    """폰 목업 밖의 베이지 배경과 그림자를 걷어 내고 목업 사각형만 남긴다.

    그림자가 배경보다 어두워 한 번에 잡으면 목업 아래 여백까지 딸려 온다.
    그래서 크게 한 번 잡은 뒤, 그 안에서 경계를 다시 정확히 짚는다.
    """
    box = _rough_box(im, tol)
    if box is None:
        return im
    return im.crop(_strip_shadow(im, box))


def _shadowish(c):
    """배경 베이지에 그림자가 덮인 색인가.

    목업 내부는 흰색(255)이나 앱 크림(밝기 243 이상)이거나 검은 바(어둡다)다.
    그림자 진 베이지만 밝기가 중간이면서 R > G > B 색조를 유지한다.
    """
    r, g, b = c
    L = (r * 299 + g * 587 + b * 114) / 1000.0
    return 150 < L < 242 and 14 <= r - b <= 48 and r >= g >= b


def _strip_shadow(im, box):
    """목업 네 변에 붙은 그림자 띠를 걷어 낸다."""
    px = im.load()
    x0, y0, x1, y1 = box

    def band(pts):
        n = len(pts)
        s = [0, 0, 0]
        for p in pts:
            c = px[p[0], p[1]]
            s[0] += c[0]
            s[1] += c[1]
            s[2] += c[2]
        return (s[0] / n, s[1] / n, s[2] / n)

    for _ in range(120):
        cx = list(range(x0 + (x1 - x0) // 3, x0 + (x1 - x0) * 2 // 3, 2))
        cy = list(range(y0 + (y1 - y0) // 3, y0 + (y1 - y0) * 2 // 3, 2))
        moved = False
        if y1 - y0 > 200 and _shadowish(band([(x, y1 - 1) for x in cx])):
            y1 -= 1
            moved = True
        if y1 - y0 > 200 and _shadowish(band([(x, y0) for x in cx])):
            y0 += 1
            moved = True
        if x1 - x0 > 200 and _shadowish(band([(x1 - 1, y) for y in cy])):
            x1 -= 1
            moved = True
        if x1 - x0 > 200 and _shadowish(band([(x0, y) for y in cy])):
            x0 += 1
            moved = True
        if not moved:
            break
    return (x0, y0, x1, y1)


def _rowdiff(im, pad=16):
    """줄마다 바로 윗줄과의 평균 색 차이를 낸다."""
    px = im.load()
    w, h = im.size
    xs = list(range(pad, w - pad, 2))
    n = float(len(xs)) * 3
    out = [999.0]
    prev = [px[x, 0] for x in xs]
    for y in range(1, h):
        cur = [px[x, y] for x in xs]
        s = 0
        for a, b in zip(prev, cur):
            s += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
        out.append(s / n)
        prev = cur
    return out


def _flat_runs(d, h, skip_top, skip_bot):
    """평평한 줄이 이어진 구간을 [(start, end)]로 모은다."""
    runs, s = [], None
    for y in range(h):
        ok = d[y] < FLAT and skip_top <= y < h - skip_bot
        if ok and s is None:
            s = y
        elif not ok and s is not None:
            if y - s >= MINRUN:
                runs.append((s + EDGE, y - EDGE))
            s = None
    if s is not None and h - skip_bot - s >= MINRUN:
        runs.append((s + EDGE, h - skip_bot - EDGE))
    return [r for r in runs if r[1] > r[0]]


def _pick(runs, need):
    """구간 길이에 비례해 손댈 줄을 고른다. 한 곳에 몰리지 않게 흩는다."""
    total = sum(b - a for a, b in runs)
    if total < need:
        return None
    picks = []
    left = need
    for i, (a, b) in enumerate(runs):
        ln = b - a
        k = need * ln // total if i < len(runs) - 1 else left
        k = min(k, ln, left)
        if k > 0:
            step = ln / float(k)
            picks += [a + int(j * step) for j in range(k)]
            left -= k
    return sorted(set(picks))[:need]


def normalize(path, out, tw=TW, th=TH):
    im = Image.open(path)
    if im.mode != 'RGB':
        bg = Image.new('RGB', im.size, (255, 255, 255))
        im = im.convert('RGBA')
        bg.paste(im, mask=im.split()[-1])
        im = bg

    ow, oh = im.size
    im = trim_mockup(im)
    w, h = im.size
    nh = int(round(h * tw / float(w)))
    im = im.resize((tw, nh), Image.LANCZOS)

    need = th - nh
    if need != 0:
        d = _rowdiff(im)
        # 상단 헤더 바와 하단 입력 바는 비율을 지켜야 자연스럽다
        runs = _flat_runs(d, nh, skip_top=int(nh * .09), skip_bot=int(nh * .06))
        picks = _pick(runs, abs(need))
        if picks is None:
            raise SystemExit('%s — 평평한 줄이 부족하다 (필요 %d)' % (path, abs(need)))
        rows = [im.crop((0, y, tw, y + 1)) for y in range(nh)]
        pset = set(picks)
        if need < 0:
            rows = [r for y, r in enumerate(rows) if y not in pset]
        else:
            grown = []
            for y, r in enumerate(rows):
                grown.append(r)
                if y in pset:
                    grown.append(r)
            rows = grown
        canvas = Image.new('RGB', (tw, th), (255, 255, 255))
        for y, r in enumerate(rows[:th]):
            canvas.paste(r, (0, y))
        im = canvas

    # 목업 라운드를 알파로 깎는다
    mask = Image.new('L', (tw, th), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, tw - 1, th - 1), RADIUS, fill=255)
    im = im.convert('RGBA')
    im.putalpha(mask)
    im.save(out, optimize=True)
    print('  %s  %dx%d  (원본 %dx%d → 목업 %dx%d, 배경줄 %+d)'
          % (out.replace('\\', '/').split('/')[-1], tw, th, ow, oh, w, h, need))


if __name__ == '__main__':
    a = sys.argv[1:]
    tw = int(a[2]) if len(a) > 2 else TW
    th = int(a[3]) if len(a) > 3 else TH
    normalize(a[0], a[1], tw, th)
