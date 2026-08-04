# -*- coding: utf-8 -*-
"""TripLinker 화면 캡처에서 브라우저 크롬을 걷어 내고 갤러리용으로 저장한다.

원본은 2560×1528 전체 창 캡처다. 위쪽 180px이 탭·주소창·북마크바이고
오른쪽 8px이 스크롤바다. 그 둘만 잘라 내면 페이지만 남는다.

사용 — python tools/triplinker_shots.py
"""
import io
import os
from PIL import Image

SRC = 'assets/프로젝트 사진/triplinker/화면 스크린샷'
OUT = 'assets/image'
CHROME_H = 181      # 북마크바 아래 구분선까지
SCROLLBAR = 8       # 오른쪽 세로 스크롤바
WIDTH = 1800        # 확대해서 봐도 글씨가 읽히는 선

SHOTS = [
    ('메인 홈 화면',            'tl-01-home'),
    ('플랜 기본정보 화면',       'tl-02-plan-basic'),
    ('플랜 취향설정 화면',       'tl-03-plan-taste'),
    ('경로 생성 로딩 화면',      'tl-04-generating'),
    ('1일차 경로',              'tl-05-day1'),
    ('모든 일차 경로 화면',      'tl-06-all-days'),
    ('순서 교체 후',            'tl-07-reorder'),
    ('실제 숙박 금액 입력',      'tl-08-stay-price'),
    ('AI 챗봇 화면',            'tl-09-chat'),
    ('AI 챗봇 예산 추가',       'tl-10-chat-budget'),
    ('가계부 화면',             'tl-11-ledger'),
    ('예산 화면',               'tl-12-budget'),
    ('수정 가능한 플랜 공유',    'tl-13-share-edit'),
    ('카카오톡 보기 권한 공유',  'tl-14-share-kakao'),
    ('커뮤니티 화면',           'tl-15-community'),
    ('후기 상세 화면',          'tl-16-review'),
    ('장소별 리뷰 목록 화면',    'tl-17-place-reviews'),
    ('관리자 대시보드 화면',     'tl-18-admin'),
    ('신고 관리 화면',          'tl-19-admin-report'),
    ('큐레이션 관리 화면',       'tl-20-admin-curation'),
]


def main():
    for src, name in SHOTS:
        p = os.path.join(SRC, src + '.png')
        im = Image.open(p).convert('RGB')
        w, h = im.size
        im = im.crop((0, CHROME_H, w - SCROLLBAR, h))
        cw, ch = im.size
        im = im.resize((WIDTH, int(round(ch * WIDTH / float(cw)))), Image.LANCZOS)
        # 지도가 깔린 화면은 PNG로 1MB를 넘는다. 사진에 가까우니 JPEG가 낫다
        out = os.path.join(OUT, name + '.png')
        im.save(out, optimize=True)
        if os.path.getsize(out) > 500 * 1024:
            os.remove(out)
            out = os.path.join(OUT, name + '.jpg')
            im.save(out, quality=88, optimize=True, progressive=True)
        print('  %-26s %dx%d  %dKB  %s' % (name, im.width, im.height,
                                           os.path.getsize(out) // 1024,
                                           os.path.splitext(out)[1]))


if __name__ == '__main__':
    main()
