# -*- coding: utf-8 -*-
"""StagePass 화면 사진을 갤러리용으로 정리한다.

원본은 브라우저 크롬이 없는 전체 페이지 캡처라 자를 데가 없다. 그대로 쓴다.
모달 두 장만 뒤에 깔린 어두운 막을 벗기고 라운드를 깎는다.

사용 — python tools/stagepass_shots.py
"""
import os
from PIL import Image
import shots

SRC = 'assets/프로젝트 사진/stagepass'
OUT = 'assets/image'

PAGES = [
    ('StagePass-공연-티켓-예매.png',      'sp-01-home'),
    ('StagePass-공연-티켓-예매8.png',     'sp-02-explore'),
    ('stagepass 티켓1.png',              'sp-03-detail'),
    ('StagePass-공연-티켓-예매 (1).png',  'sp-04-seats'),
    ('StagePass-공연-티켓-예매 (3).png',  'sp-07-myticket'),
    ('StagePass-공연-티켓-예매 (5).png',  'sp-08-guide'),
    ('StagePass-공연-티켓-예매 (6).png',  'sp-09-refund'),
    ('StagePass-공연-티켓-예매 (4).png',  'sp-10-faq'),
]

MODALS = [
    ('StagePass-공연-티켓-예매7.png',     'sp-05-booking'),
    ('StagePass-공연-티켓-예매 (2).png',  'sp-06-confirm'),
]


def main():
    for src, name in PAGES:
        im = Image.open(os.path.join(SRC, src)).convert('RGB')
        shots.save(im, os.path.join(OUT, name))
    for src, name in MODALS:
        im = Image.open(os.path.join(SRC, src)).convert('RGB')
        im = im.crop(shots.card_box(im))
        r = shots.white_radius(im)
        im = shots.round_corners(im, r)
        shots.save(im, os.path.join(OUT, name))
        print('     라운드 %dpx' % r)


if __name__ == '__main__':
    main()
