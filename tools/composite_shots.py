# -*- coding: utf-8 -*-
"""그림판에서 한 장으로 붙여 놓은 합성 캡처를 화면별로 되쪼갠다.

패널이 서로 붙어 있고 배경도 흰색이라 자동 분리로는 경계가 흐려진다.
그래서 좌표를 손으로 박고, 그 안에서 흰 여백만 깎아 낸다.
원본 픽셀을 그대로 쓰므로 화질이 떨어지지 않는다.

사용 — python tools/composite_shots.py [windycamp|deviceshop|petvillage|all]
"""
import os
import sys
from PIL import Image
import shots

SRC = 'assets/프로젝트 사진'
OUT = 'assets/image'

# (파일, [(이름, (x0, y0, x1, y1)), ...])
PLANS = {
    'windycamp': ('windycamp.png', [
        ('wc-01-main',    (0, 0, 1802, 784)),
        ('wc-02-list',    (1858, 32, 2978, 1112)),
        ('wc-03-detail',  (0, 792, 1566, 1444)),
        ('wc-04-zipcode', (22, 1528, 690, 2114)),
        ('wc-05-signup',  (688, 1548, 1206, 2462)),
        ('wc-06-admin',   (1586, 1146, 2722, 2448)),
    ]),
    'deviceshop': ('DEVICE SHOP.png', [
        ('ds-01-main',     (16, 40, 1198, 872)),
        ('ds-02-sales',    (1204, 40, 2364, 872)),
        ('ds-03-login',    (2380, 34, 2976, 680)),
        ('ds-04-products', (18, 888, 1966, 1782)),
        ('ds-05-chart',    (18, 1808, 1906, 2628)),
        ('ds-06-home',     (18, 2712, 1966, 3558)),
    ]),
    'petvillage': ('PetVillage.png', [
        ('pv-01-ai-name',   (0, 0, 1146, 873)),
        ('pv-02-chatbot',   (1146, 0, 2303, 873)),
        ('pv-03-animals',   (2308, 0, 3485, 873)),
        ('pv-04-ai-result', (0, 885, 1180, 1659)),
        ('pv-05-guide',     (1180, 885, 2369, 1752)),
        ('pv-06-reviews',   (2371, 885, 3547, 1754)),
        ('pv-07-centers',   (0, 1669, 1180, 2533)),
        ('pv-08-donate',    (1180, 1760, 2369, 2624)),
        ('pv-09-login',     (2374, 1830, 2718, 2320), 'modal'),
        ('pv-10-signup',    (2734, 1860, 3068, 2314), 'modal'),
        ('pv-11-admin',     (23, 2631, 1224, 3461)),
    ]),
}


def run(key):
    src, rects = PLANS[key]
    im = Image.open(os.path.join(SRC, src)).convert('RGB')
    for r in rects:
        name, box = r[0], r[1]
        kind = r[2] if len(r) > 2 else 'page'
        c = im.crop(box)
        if kind == 'modal':
            # 어두운 막 위에 뜬 모달은 흰 카드 영역을 찾아 자르고 코너를 깎는다
            c = c.crop(shots.card_box(c))
            c = shots.round_corners(c, shots.white_radius(c))
        elif kind == 'page':
            c = shots.trim_white(c)
        # 'exact'는 좌표 그대로 쓴다 — 흰 배경 위의 흰 카드는 자동 판정이 어긋난다
        shots.save(c, os.path.join(OUT, name))


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for k in (PLANS if what == 'all' else [what]):
        print(k)
        run(k)
