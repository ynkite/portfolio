# -*- coding: utf-8 -*-
"""제출용 요약 포트폴리오를 조판한다. 19쪽.

전체판(build_pdf.py)이 88쪽이라 면접 자리에서 넘겨 보기엔 길다.
이 판은 「무엇을 만들었고, 무엇을 재서, 얼마가 나왔나」만 남긴다.

  1쪽   표지 · 프로필 · 사진을 한 판에
  2쪽   자격 · 수상 · 교육 · 스킬을 한 판에
  3~7   COGI
  8~12  TripLinker
  13~17 오몽
  18쪽  더 많은 작업
  19쪽  링크 · 연락처

프로젝트마다 다섯 쪽으로 못 박는다.
  ① 표지 + 개요 + 대표 수치      ② 실제 화면 여섯 장
  ③ 설계 + 담당 파트             ④ 개발과 평가 (수치 · 그래프)
  ⑤ 문제 해결 + 배포 · 테스트

조판 방식은 전체판과 다르다. 한 쪽 = 한 블록으로 못 박아 조판기가 쪼개지 못하게 한다.
쪽 수를 정확히 통제하려면 이 편이 낫다.

  python tools/build_summary.py
"""
import io
import os
import re
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdfkit
import pdfdoc
import summary_css
from pdfkit import Block

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
PDF = '포트폴리오_정상연_요약.pdf'
SITE = 'https://ynkite.github.io/portfolio/'
IMGDIR = '_sumimg'
NL = chr(10)

CH = [
    dict(no='01', sec='work', file='projects/cogi.html', name='COGI', brand='#1c4f8c',
         kicker='AI 코드리뷰 학습 플랫폼'),
    dict(no='02', sec='triplinker', file='projects/triplinker.html', name='TripLinker',
         brand='#a85c28', kicker='AI 여행 플래너'),
    dict(no='03', sec='omong', file='projects/omong.html', name='오몽', brand='#E07B1E',
         kicker='키오스크 주문 도우미'),
]

# 장마다 대표 수치 세 개. 전부 지면에 근거가 있는 값이다
# 사이트 개요에 수치 칸이 없는 프로젝트는 여기서 채운다.
# 표지에 실은 것과 겹치지 않게 다른 값을 고른다.
INTRO_NUMS = {
    'omong': [('52장', '카페 · 병원 · 주민센터 키오스크 사진'),
              ('729ms', '응답 중앙값 · 규칙 폴백 경로'),
              ('5개국어', '한국어 · 영어 · 중국어 · 베트남어 · 일본어')],
}

STATS = {
    'work': [('138문항', '직접 만든 평가셋'),
             ('100%', '카드 생성 성공 · 68/68'),
             ('180건', '테스트 케이스 · 96% 통과')],
    'triplinker': [('250문항', '직접 만든 평가셋'),
                   ('11.4% → 100%', '장소 실재율 · 모델 단독 대비'),
                   ('41% → 100%', '일정 생성률 · 세 회차')],
    'omong': [('52장', '키오스크 사진 평가셋'),
              ('100%', '스키마 준수 · 규칙 폴백 응답'),
              ('2박 3일', '해커톤 · 아이디어상 · 팀 MVP')],
}

# 실제 화면. 한 쪽에 여섯 장을 격자로 놓는다
SHOTS = {
    'work': [('cogi-01-dashboard.png', '대시보드'),
             ('cogi-04-review.png', 'AI 리뷰 결과'),
             ('cogi-06-learning-card.png', '학습 카드'),
             ('cogi-07-skill-recommend.png', 'AI 스킬 추천'),
             ('cogi-08-weekly-report.png', '주간 리포트 메일'),
             ('cogi-02-retention.png', '리텐션 · streak')],
    'triplinker': [('tl-02-plan-basic.png', '플랜 만들기'),
                   ('tl-03-plan-taste.png', '취향 설정'),
                   ('tl-05-day1.jpg', '1일차 경로'),
                   ('tl-07-reorder.jpg', '장소 순서 교체'),
                   ('tl-09-chat.png', 'AI 챗봇'),
                   ('tl-11-ledger.png', '가계부')],
    'omong': [('omong-01-home.png', '홈'),
              ('omong-04-narrow.png', '메뉴 좁히기'),
              ('omong-06-guide2.png', '화면 안내'),
              ('omong-08-staff.png', '직원에게 보여주기'),
              ('omong-10-vision.png', '사진 인식'),
              ('omong-02-bigtext.png', '큰글씨 모드')],
}

TILE_SHOTS = {
    'stagepass': 'sp-01-home-crop.jpg', 'windycamp': 'wc-03-detail.jpg',
    'deviceshop': 'ds-02-sales.jpg', 'petvillage': 'pv-01-ai-name.jpg',
    'triplan': 'triplan-01-main.png', 'festa': 'festa-01-paper.png',
}


# ────────────────────────────── 읽기 ──────────────────────────────

def read(p):
    return io.open(os.path.join(ROOT, p), encoding='utf-8').read()


def untag(s):
    # <br> 를 그냥 지우면 앞뒤 낱말이 붙는다 — 「지적을약점으로」 같은 것
    s = re.sub(r'<br\s*/?>', ' ', s or '')
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def keepb(s):
    """굵게 강조한 낱말은 살리고 나머지 태그만 턴다."""
    s = re.sub(r'<(?!/?b[ >])[^>]*>', '', s or '')
    return re.sub(r'\s+', ' ', s).strip()


def sec_of(pj, key):
    for s in pj['sections']:
        if key in s['step']:
            return s
    return None


def blocks_of(sec, kind):
    return [b for b in (sec['blocks'] if sec else []) if b['t'] == kind]


def shrink(html):
    """지면에 실리는 사진을 인쇄 크기에 맞춰 줄인다. 원본을 그대로 넣으면 파일이 커진다."""
    dst = os.path.join(ROOT, IMGDIR)
    if not os.path.isdir(dst):
        os.makedirs(dst)
    seen = {}

    def one(m):
        src = m.group(1)
        if src.startswith('data:'):
            return m.group(0)
        if src in seen:
            return m.group(0).replace(src, seen[src])
        p = os.path.join(ROOT, src.replace('/', os.sep))
        if not os.path.exists(p):
            return m.group(0)
        name = re.sub(r'[^A-Za-z0-9._-]', '_', src)
        out = os.path.join(dst, name)
        try:
            im = Image.open(p)
            im.thumbnail((1400, 1400), Image.LANCZOS)
            if im.mode in ('RGBA', 'P'):
                im = im.convert('RGB')
            im.save(out, 'JPEG', quality=76, optimize=True)
        except Exception:
            shutil.copy(p, out)
        rel = (IMGDIR + '/' + name).replace(os.sep, '/')
        seen[src] = rel
        return m.group(0).replace(src, rel)

    return re.sub(r'src="([^"]+)"', one, html)


# ────────────────────────────── 쪽 ──────────────────────────────

SITE = 'ynkite.github.io/portfolio'


def page_cover(pr):
    """1쪽 — 표지와 프로필을 한 판에.

    왼쪽 기둥에 사진 · 연락처 · 사이트 주소를 세우고, 오른쪽에 이름과 이력을 편다.
    사이트 주소는 눌러서 바로 열리도록 링크로 넣고 가장 눈에 띄게 둔다.
    """
    parts = [x.strip() for x in pr.get('연락처', '').split('·')]
    mail = next((x for x in parts if '@' in x), '')
    tel = next((x for x in parts if '@' not in x), '')
    rows = [('학력', pr.get('학력', '')), ('교육', pr.get('교육', '')),
            ('경력', pr.get('경력', '')), ('자격 · 수상', pr.get('자격증 · 수상', ''))]
    IDX = (('01', 'COGI', 'AI 코드리뷰 학습 플랫폼', '팀장 · 백엔드 · AI 연동', '03'),
           ('02', 'TripLinker', 'AI 여행 플래너', '백엔드 · AI 연동', '09'),
           ('03', '오몽', '키오스크 주문 도우미', '팀장 · 백엔드 · 비전', '15'))
    idx = ''.join('<li><b>%s</b><span>%s<i>%s</i></span><em>%s쪽</em></li>'
                  % (n, nm, sub, pg) for n, nm, sub, _, pg in IDX)
    return ('<div class="cv">'
            '<div class="cvL">'
            '<div class="cvphoto"><img src="assets/profile.jpg" alt="정상연"></div>'
            '<dl class="cvct">'
            '<div><dt>메일</dt><dd>%s</dd></div>'
            '<div><dt>전화</dt><dd>%s</dd></div>'
            '<div><dt>깃허브</dt><dd>%s</dd></div>'
            '<div><dt>블로그</dt><dd>%s</dd></div>'
            '</dl>'
            '<a class="cvsite" href="https://%s">'
            '<span class="cvsk">포트폴리오 사이트</span>'
            '<span class="cvsu">%s</span>'
            '<span class="cvsn">프로젝트 상세 · 평가셋 결과 · 산출물<i>↗</i></span></a>'
            '</div>'
            '<div class="cvR">'
            '<div class="cvrole">Backend Developer · AI Agent Engineer</div>'
            '<h1 class="cvname">정상연</h1>'
            '<div class="cven">Jeong Sangyeon · 2001.08.02</div>'
            '<p class="cvlead">AI 기능을 서비스에 붙이고, 그 결과를 수치로 확인하는 백엔드 개발자입니다.'
            '<br>모델을 새로 학습시키기보다 이미 있는 모델을 서비스 안에서 안정적으로 돌리는 일을 해 왔습니다.'
            '<br>벤더 호출이 실패해도 화면이 멈추지 않도록 폴백과 응답 검증 계층을 설계했습니다.</p>'
            '<div class="cvnums">'
            '<div><b>3</b><span>팀 프로젝트<br>전부 AWS 배포</span></div>'
            '<div><b>440문항</b><span>세 프로젝트에 쓴<br>직접 만든 평가셋</span></div>'
            '<div><b>2</b><span>팀장을 맡은<br>프로젝트</span></div>'
            '</div>'
            '<div class="cvrows">%s</div>'
            '<ol class="cvidx">%s</ol>'
            '</div></div>'
            % (mail, tel, pr.get('GitHub', ''), pr.get('기술 블로그', ''), SITE, SITE,
               ''.join('<div class="cvrow"><b>%s</b><span>%s</span></div>' % kv
                       for kv in rows), idx))


# 축은 2024년 3월(입학)에서 시작해 2026년 8월(지금)까지 30개월이다.
TL_A, TL_B = 2024 * 12 + 3, 2026 * 12 + 8


def _mo(v):
    """2025.06 → 축 위 위치(%). 축 밖이면 None."""
    m = re.match(r'(\d{4})\.(\d{1,2})', v or '')
    if not m:
        return None
    n = int(m.group(1)) * 12 + int(m.group(2))
    if n < TL_A or n > TL_B:
        return None
    return (n - TL_A) * 100.0 / (TL_B - TL_A)


def _span(a, b):
    x, y = _mo(a), _mo(b)
    x = 0.0 if x is None else x
    y = 100.0 if y is None else y
    return x, max(y - x, 2.0)


def page_credits(cr, cats):
    """2쪽 — 연표. 축 하나를 왼쪽에서 오른쪽으로 긋고 그 위아래에 붙인다.

    위: 자격증과 수상. 같은 달에 몰린 것은 층을 올려 서로 비키게 한다.
    아래: 기간이 있는 것(학교 · 일 · 교육)을 막대로 깐다.
    """
    ev = []
    for g, kind in ((cr[0], "cert"), (cr[1], "award")):
        for r in g['rows']:
            x = _mo(r['val'])
            if x is None:
                continue
            # 연표 칸은 좁다. 앞에 붙은 연도와 군더더기를 뗀다.
            nm = re.sub(r'^20\d\d ', '', r['nm'])
            nm = nm.replace('언어 사용 설명서 경진대회', '설명서 경진대회')
            nm = nm.replace('빛나는 인재 AI Re-Local 해커톤', 'AI Re-Local 해커톤')
            nm = nm.replace('Analyze Festa 데이터 분석 경진대회', 'Analyze Festa')
            nm = nm.replace('Laravel 웹 솔루션 경진대회', 'Laravel 경진대회')
            nm = nm.replace('AWS 서비스 활용능력 경진대회', 'AWS 경진대회')
            nm = nm.replace('MOS 365 Word Expert', 'MOS Word Expert')
            ev.append((x, r['val'], nm, r['tag'], kind))
    ev.sort()

    # 층 배정 — 왼쪽부터 훑으며 아직 자리가 빈 가장 낮은 층에 놓는다.
    GAP = 13.5   # 이만큼 떨어져야 같은 층에 나란히 설 수 있다 (%)
    last = []
    tier = []
    for x, _, _, _, _ in ev:
        for t in range(len(last)):
            if x - last[t] >= GAP:
                last[t] = x
                tier.append(t)
                break
        else:
            last.append(x)
            tier.append(len(last) - 1)
    top = max(tier) + 1 if tier else 1

    marks = ""
    for (x, val, nm, tag, kind), t in zip(ev, tier):
        pull = -6 if x < 6 else (-94 if x > 94 else -50)
        yy, mm = val.split('.')
        marks += ('<div class="tlev t%d %s" style="left:%.2f%%">'
                  '<div class="tlcard" style="transform:translateX(%d%%)">'
                  '<u>%s월</u><b>%s</b><em>%s</em></div>'
                  '<i style="height:%dpx"></i></div>'
                  % (t, kind, x, pull, mm.lstrip('0'), nm, tag, 16 + t * 52))

    ticks = ""
    for y in (2024, 2025, 2026):
        for m in (1, 4, 7, 10):
            x = _mo('%d.%02d' % (y, m))
            if x is None:
                continue
            big = (m == 1) or (y == 2024 and m == 4)
            lab = str(y) if big else '%d분기' % ((m - 1) // 3 + 1)
            ticks += ('<div class="tk%s" style="left:%.2f%%"><span>%s</span></div>'
                      % (' big' if big else '', x, lab))

    BARS = (('인덕대학교 컴퓨터소프트웨어학과', '2024.03', '2027.02',
             '학점 3.73 / 4.5 · 전공 동아리 회장 · 스터디 팀장 · 전공 멘토', '재학 중'),
            ('JS무역 · 그래픽 디자인', '2025.04', '2025.10',
             '중국어 조립 설명서 번역 · 재디자인 · 상품 상세 페이지 제작', '7개월'),
            ('대우능력개발원 KDT · AI 에이전트 클라우드 · 보안코딩', '2025.11', '2026.08',
             'Java · Spring Boot · Spring AI · AWS · 실무형 팀 프로젝트 312시간', '1024시간'))
    bars = ""
    for nm, a, b, sub, tag in BARS:
        x, wd = _span(a, b)
        open_end = ' open' if _mo(b) is None else ''
        # 설명이 오른쪽으로 넘칠 것 같으면 왼쪽 대신 오른쪽 끝에 붙인다.
        est = sum(2 if ord(ch) > 0x2000 else 1 for ch in sub) * 5.2
        pos = ('right:0' if x / 100.0 * 910 + est > 906
               else 'left:%.2f%%' % x)
        bars += ('<div class="tlrow"><div class="tlbar%s" style="left:%.2f%%;width:%.2f%%">'
                 '<b>%s</b><em>%s</em></div>'
                 '<div class="tlsub" style="%s">%s</div></div>'
                 % (open_end, x, wd, nm, tag, pos, sub))

    sk = ""
    for c in cats:
        core = ' · '.join(n for _, n, k in c['items'] if k)
        rest = ' · '.join(n for _, n, k in c['items'] if not k)
        # 갈래마다 한 줄. 주력을 앞에 진하게 두고 나머지를 뒤에 붙인다.
        sk += ('<div class="skrow"><h4>%s</h4><p><b>%s</b>%s</p></div>'
               % (c['name'], core or rest,
                  ('<span> · %s</span>' % rest) if (core and rest) else ''))

    return ('<div class="sheet"><div class="shd"><div class="kick">Timeline</div>'
            '<h2>2024년 3월부터</h2><p>자격증과 수상은 위쪽에, '
            '학교와 일, 교육 기간은 아래 막대에 표시했습니다.</p></div>'
            '<div class="tl" style="--tiers:%d">'
            '<div class="tlmarks">%s</div>'
            '<div class="tlaxis">%s</div>'
            '<div class="tlbars">%s</div></div>'
            '<div class="skwrap"><div class="mt2">Skills — 진한 쪽이 주력입니다</div>'
            '<div class="skgrid">%s</div></div></div>'
            % (top, marks, ticks, bars, sk))


# 사이트에서 프로젝트 상세로 바로 가는 주소. 시연 영상은 그 안의 #video 로 간다.
# 실제로 들어가서 눌러 볼 수 있게 열어 둔 계정.
# 트립링커는 AI 호출 비용 때문에 일정 생성만 막아 두고 나머지는 그대로 돈다.
DEMO = {
    'work': ('user@a.a', '1234', ''),
    'triplinker': ('user01', '1234',
                   '챗봇 대화까지 되고, 일정은 미리 넣어 둔 것이 뜹니다'),
}

PROJ_URL = {'work': 'projects/cogi.html',
            'triplinker': 'projects/triplinker.html',
            'omong': 'projects/omong.html'}


def proj_link(sec, anchor=""):
    p = PROJ_URL.get(sec)
    return ('https://%s/%s%s' % (SITE, p, anchor)) if p else ''


def page_chapter(ch, pj):
    """프로젝트 표지 — 색을 지면에 도배하지 않는다.

    왼쪽 가장자리에 브랜드 색 띠 하나만 세우고, 나머지는 본문 쪽과 같은
    흰 바탕 · 실선 규칙으로 간다. 장이 바뀌는 것은 띠 색과 번호로 안다.
    """
    stats = ''.join('<div><b>%s</b><span>%s</span></div>' % kv for kv in STATS[ch['sec']])
    chips = ' · '.join(re.findall(r'<span[^>]*>(.*?)</span>', pj['chips'] or ''))
    raw = untag(pj['meta'])
    sep = r'\s*\|\s*' if '|' in raw else r'\s+·\s+'
    parts = [x.strip() for x in re.split(sep, raw) if x.strip()]
    when = ' · '.join(parts[:2])
    role = parts[2] if len(parts) > 2 else ''
    urls = re.findall(r'href="([^"]+)"', pj['links'] or '')
    urls = list(dict.fromkeys(urls))   # 같은 주소가 두 번 걸린다
    addr = ''.join(
        '<a href="%s">%s</a>' % (u, u.replace('https://', '').replace('http://', '').rstrip('/'))
        for u in urls)
    rows = (('담당 파트', role), ('기간 · 팀', when), ('기술', chips))
    meta = ''.join('<div class="cvrow"><b>%s</b><span>%s</span></div>' % kv
                   for kv in rows if kv[1])
    meta += '<div class="cvrow addr"><b>주소</b><span>%s</span></div>' % addr
    d = DEMO.get(ch['sec'])
    if d:
        note = ('<i>%s</i>' % d[2]) if d[2] else ''
        meta += ('<div class="cvrow demo"><b>테스트 계정</b>'
                 '<span><u>%s</u> / <u>%s</u>%s</span></div>' % (d[0], d[1], note))
    return ('<div class="chpg">'
            '<div class="chhd"><em>%s</em><i></i><span>%s</span></div>'
            '<h1 class="chname">%s</h1>'
            '<p class="chdesc">%s</p>'
            '<div class="chmeta">%s</div>'
            '<div class="chstats big%s">%s</div></div>'
            % (ch['no'], ch['kicker'], pj['name'], pj['desc'], meta,
               # 값이 길면 한 줄에 안 들어간다. 그만큼 글자를 줄인다.
               ' sm' if max(len(k) for k, _ in STATS[ch['sec']]) > 9 else '',
               stats))


def links_text(html):
    urls = re.findall(r'href="([^"]+)"', html or '')
    return ' · '.join(u.replace('https://', '').replace('http://', '').rstrip('/') for u in urls)


def page_intro(ch, pj):
    """프로젝트 ② — 서비스 소개와 주요 기능."""
    ov = sec_of(pj, 'OVERVIEW')
    fe = sec_of(pj, 'FEATURES')
    feats = ''
    fb = blocks_of(fe, 'feats')
    if fb:
        for i, el in enumerate(fb[0]['items'], 1):
            inner = re.sub(r'^\s*<div[^>]*>|</div>\s*$', '', el.strip())
            m = re.match(r'\s*<b>(.*?)</b>(.*)$', inner, re.S)
            if not m:
                continue
            feats += ('<div class="frow"><u>%02d</u><b>%s</b><span>%s</span></div>'
                      % (i, untag(m.group(1)), keepb(m.group(2))))
    ovb = blocks_of(ov, 'ov')
    nums = ''
    if ovb:
        for c in re.findall(r'<div class="c">(.*?)</div>\s*(?=<div class="c">|$)',
                            ovb[0]['html'], re.S)[:4]:
            b = re.search(r'<b[^>]*>(.*?)</b>', c, re.S)
            sp = re.search(r'<span[^>]*>(.*?)</span>', c, re.S)
            if b:
                nums += ('<div><b>%s</b><span>%s</span></div>'
                         % (untag(b.group(1)), untag(sp.group(1)) if sp else ''))
    if not nums:
        # 사이트 쪽에 수치 칸이 없으면 미리 정해 둔 값으로 채운다
        for k, v in INTRO_NUMS.get((ch or {}).get('sec', ''), []):
            nums += '<div><b>%s</b><span>%s</span></div>' % (k, v)
    airy = ' airy' if (not nums and feats.count('frow') <= 6) else ''
    return ('<div class="sheet%s"><div class="shd"><div class="kick">Overview</div>'
            '<h2>프로젝트 소개</h2>'
            '<p class="shlead">%s</p></div>'
            '%s'
            '<div class="mt2">주요 기능</div>'
            '<div class="fgrid">%s</div></div>'
            % (airy, ov['lead'] if ov else '',
               ('<div class="chstats">%s</div>' % nums) if nums else '', feats))


# 세로로 긴 화면을 쓰는 프로젝트. 여섯 장을 두 줄로 놓으면 높이에 걸려 아주 작아진다.
# 넉 장만 한 줄에 놓으면 같은 지면에서 두 배 넘게 커진다.
TALL = {'omong': 4}


def page_shots(ch):
    """프로젝트 ② — 실제 화면 여섯 장을 한 쪽에."""
    cells = ''
    n = TALL.get(ch['sec'])
    for f, cap in SHOTS[ch['sec']][:n]:
        cells += ('<figure class="sc"><div class="scimg"><img src="assets/image/%s" alt="%s"></div>'
                  '<figcaption>%s</figcaption></figure>' % (f, cap, cap))
    return ('<div class="sheet"><div class="shd"><div class="kick">Screens</div>'
            '<h2>실제 화면</h2>%s</div><div class="scgrid%s">%s</div></div>'
            % (('<a class="shlink" href="%s">소개 · 시연 영상 ↗</a>'
                % proj_link(ch['sec'], '#video')), ' tallshots' if n else '', cells))


def clip_sentences(html, budget=118):
    """칸에 안 들어가는 설명은 문장 단위로 줄인다.

    화면에서 잘라 내면 「…합칩니」 처럼 낱말 한가운데가 끊긴다.
    마침표를 기준으로 앞에서부터 담고, 넘치면 그 문장은 버린다.
    한 문장도 못 담을 만큼 길면 그 한 문장은 그대로 둔다.
    """
    if not html:
        return html
    parts = re.split(r'(?<=[.])\s+', html.strip())
    out, used = [], 0
    for x in parts:
        n = len(re.sub(r'<[^>]+>', '', x))
        if out and used + n > budget:
            break
        out.append(x)
        used += n
    return ' '.join(out)


def page_design(pj):
    """프로젝트 ③ — 설계와 담당 파트. 도식은 싣지 않는다."""
    ds = sec_of(pj, 'DESIGN')
    mp = sec_of(pj, 'MY PART')
    cards = ''
    cb = blocks_of(ds, 'cards')
    if cb:
        for el in cb[0]['items'][:6]:
            n = untag(re.search(r'<div class="n">(.*?)</div>', el, re.S).group(1)) \
                if '<div class="n">' in el else ''
            h = untag(re.search(r'<h3>(.*?)</h3>', el, re.S).group(1)) if '<h3>' in el else ''
            p = re.search(r'<p>(.*?)</p>', el, re.S)
            cards += ('<div class="dcard"><div class="dn">%s</div><b>%s</b><p>%s</p></div>'
                      % (n, h, clip_sentences(p.group(1)) if p else ''))
    parts = ''
    pb = blocks_of(mp, 'parts')
    if pb:
        for el in pb[0]['items'][:7]:
            h = untag(re.search(r'<h3>(.*?)</h3>', el, re.S).group(1)) if '<h3>' in el else ''
            lis = re.findall(r'<li>(.*?)</li>', el, re.S)
            parts += ('<div class="prow"><b>%s</b><span>%s</span></div>'
                      % (h, ' · '.join(untag(x) for x in lis[:2])))
    return ('<div class="sheet"><div class="shd"><div class="kick">Design · My Part</div>'
            '<h2>설계와 담당 파트</h2></div>'
            '<div class="dgrid">%s</div>'
            '<h3 class="mt2">담당 파트</h3><div class="plist">%s</div></div>'
            % (cards, parts))


def page_eval(pj, brand):
    """프로젝트 ④ — 개발과 평가. 수치와 그래프만."""
    ev = sec_of(pj, 'DEVELOPMENT')
    graph = ''
    tables = []
    for b in (ev['blocks'] if ev else []):
        if b['t'] not in ('raw', 'ov'):
            continue
        h = b['html']
        m = re.search(r'<svg class="trend".*?</svg>', h, re.S)
        if m and not graph:
            graph = m.group(0)
        for t in re.findall(r'<table class="evt">.*?</table>', h, re.S):
            tables.append(t)
    keep = tables[:2]
    # 줄이 적으면 지면이 남는다. 그만큼 줄 간격을 벌려 아래를 비우지 않는다.
    lines = sum(len(re.findall(r'<tr', t)) for t in keep)
    airy = ' airy' if (lines <= 9 and not graph) else ''
    if graph and lines >= 10:
        airy += ' tight'      # 줄이 많으면 그래프를 줄여 담는다
    return ('<div class="sheet%s" style="--brand:%s"><div class="shd"><div class="kick">Evaluation</div>'
            '<h2>개발과 평가</h2>'
            '<p class="shlead">평가셋을 돌려 문제를 찾고, 고친 다음 같은 평가셋을 한 번 더 돌렸습니다.</p></div>'
            '%s<div class="etabs">%s</div></div>'
            % (airy, brand, ('<div class="egraph">%s</div>' % graph) if graph else '',
               ''.join(keep)))


def sentence_breaks(html):
    """한 줄에 안 들어가는 설명은 문장 끝에서 나눈다.

    마침표 뒤에 공백이 오고 다음이 태그나 글자면 그 자리에서 줄을 바꾼다.
    `abc.def()` 처럼 코드 안에 든 마침표는 뒤에 공백이 없으니 걸리지 않는다.
    """
    if not html:
        return html
    out = re.sub(r'(?<=[.])\s+(?=\S)', '<br>', html)
    return re.sub(r'(<br>)+$', '', out)


def page_trouble(pj):
    """프로젝트 ⑤ — 문제 해결과 배포."""
    ev = sec_of(pj, 'DEVELOPMENT')
    dp = sec_of(pj, 'DEPLOY')
    items = ''
    tb = blocks_of(ev, 'ts')
    if tb:
        for el in tb[0]['items'][:4]:
            t = untag(re.search(r'<div class="t">(.*?)</div>', el, re.S).group(1)) \
                if '<div class="t">' in el else ''
            got = {}
            for m in re.finditer(r'<div class="lab">([^<]*)</div>\s*<p>(.*?)</p>', el, re.S):
                got[m.group(1).strip()] = sentence_breaks(re.sub(r'<br\s*/?>', ' ', m.group(2)).strip())
            items += ('<div class="tcard"><b>%s</b>'
                      '<div class="trow"><em>원인</em><span>%s</span></div>'
                      '<div class="trow"><em>해결</em><span>%s</span></div></div>'
                      % (re.sub(r'^[①-⑳]\s*', '', t), got.get('원인', ''), got.get('해결', '')))
    drows = ''
    for b in blocks_of(dp, 'dtable')[:1]:
        for el in b['items'][:5]:
            k = re.search(r'<span class="k">(.*?)</span>', el, re.S)
            v = re.search(r'<span class="v">(.*?)</span>', el, re.S)
            if k and v:
                drows += ('<div class="mrow"><b>%s</b><span>%s</span></div>'
                          % (untag(k.group(1)),
                             sentence_breaks(re.sub(r'<br\s*/?>', ' ', v.group(1)))))
    return ('<div class="sheet"><div class="shd"><div class="kick">Troubleshooting · Deploy</div>'
            '<h2>문제 해결과 배포</h2></div>'
            '<div class="tgrid">%s</div>'
            '<h3 class="mt2">배포 · 테스트</h3><div class="dep">%s</div></div>'
            % (items, drows))


def page_more(tiles):
    """18쪽 — 더 많은 작업. 여섯 개를 한 쪽에."""
    cells = ''
    for el in tiles:
        m = re.search(r'data-lb="(\w+)"', el)
        key = m.group(1) if m else ''
        nm = untag(re.search(r'<h3>(.*?)</h3>', el, re.S).group(1)) if '<h3>' in el else ''
        meta = re.search(r'<div class="tmeta">(.*?)</div>', el, re.S)
        p = re.search(r'<p>(.*?)</p>', el, re.S)
        img = TILE_SHOTS.get(key)
        cells += ('<div class="mcard">%s<b>%s</b><span class="mm">%s</span><p>%s</p></div>'
                  % (('<div class="mimg"><img src="assets/image/%s" alt=""></div>' % img) if img else '',
                     nm, untag(meta.group(1)) if meta else '',
                     untag(p.group(1))[:74] if p else ''))
    return ('<div class="sheet"><div class="shd"><div class="kick">More Work</div>'
            '<h2>더 많은 작업</h2></div><div class="mgrid">%s</div></div>' % cells)


def page_links(pr):
    """마지막 쪽 — 사이트 주소와 연락처.

    종이로 본 사람이 곧바로 사이트로 넘어오게 하는 것이 이 쪽의 목적이다.
    그래서 주소 하나가 지면의 절반을 쓴다. 눌러서 바로 열린다.
    """
    LK = (('GitHub', 'github.com/ynkite', '프로젝트 소스와 커밋 기록',
           'https://github.com/ynkite'),
          ('기술 블로그', 'my-commit.tistory.com', '막힌 곳과 푼 방법 200편',
           'https://my-commit.tistory.com'),
          ('메일', 'j.sangyeon6@gmail.com', '', 'mailto:j.sangyeon6@gmail.com'),
          ('전화', '010-4211-3521', '', ''))
    rows = ''
    for nm, val, sub, href in LK:
        tag = 'a href="%s"' % href if href else 'div'
        rows += ('<%s class="lrow"><b>%s</b><span>%s</span><em>%s</em></%s>'
                 % (tag, nm, val, sub, tag.split(' ')[0]))
    return ('<div class="sheet endpage"><div class="shd"><div class="kick">Contact</div>'
            '<h2>연락처</h2>'
            '<p class="shlead">포트폴리오 사이트에 모든 내용을 자세히 올려 뒀습니다.</p></div>'
            '<a class="bigsite" href="https://%s">'
            '<span class="bsk">Portfolio</span>'
            '<span class="bsu">%s</span>'
            '<span class="bsn">포트폴리오 사이트입니다<i>↗</i></span></a>'
            '<div class="lgrid">%s</div></div>'
            % (SITE, SITE, rows))


# ─────────────────────────── 조립 ───────────────────────────

def render(pages, brands):
    """한 쪽 = 한 판. 브랜드 색 전면 쪽과 레일을 여기서 붙인다."""
    out = []
    n = len(pages)
    for i, (tag, html, kind) in enumerate(pages, 1):
        brand = brands.get(tag, '')
        st = (' style="--brand:%s"' % brand) if brand else ''
        cls = 'page'
        rail = ''
        if kind == 'brandfill':
            # 장 표지 — 색 띠만 세우고 판면은 흰 바탕 그대로 쓴다
            cls += ' chapter'
        else:
            if kind:
                cls += ' ' + kind
            if brand:
                cls += ' hasrail'
                rail = ('<div class="rail"><span class="rl">%s</span><i></i>'
                        '<span class="rn">%02d</span></div>' % (tag, i))
        foot = ('<div class="pfoot"><span>포트폴리오</span>'
                '<b>%s</b><span>%02d / %02d</span></div>' % (tag, i, n))
        out.append('<section class="%s"%s>%s<div class="pgbody">%s</div>%s</section>'
                   % (cls, st, rail, html, foot))
    return ''.join(out)

def build():
    pr = pdfdoc.profile()
    cr = pdfdoc.credits()
    cats, _ = pdfdoc.skills()
    ix = pdfdoc.index_parts()

    pages = [('프로필', page_cover(pr), ''),
             ('경력 · 자격', page_credits(cr, cats), 'gray')]
    brands = {}
    for ch in CH:
        pj = pdfdoc.project(ch['file'])
        tag = ch['name']
        brands[tag] = ch['brand']
        pages += [(tag, page_chapter(ch, pj), 'brandfill'),
                  (tag, page_intro(ch, pj), 'gray'),
                  (tag, page_shots(ch), 'gray'),
                  (tag, page_design(pj), ''),
                  (tag, page_eval(pj, ch['brand']), ''),
                  (tag, page_trouble(pj), 'gray')]
    pages.append(('더 많은 작업', page_more(ix['tiles']), 'gray'))
    pages.append(('링크 · 연락처', page_links(pr), ''))
    return pages, brands


def main():
    os.chdir(ROOT)
    if os.path.isdir(os.path.join(ROOT, IMGDIR)):
        shutil.rmtree(os.path.join(ROOT, IMGDIR))
    pages, brands = build()
    body = render(pages, brands)
    css = summary_css.CSS.replace('__BODYH__', str(int(pdfkit.PAGE_H) - 62 - 56))
    html = ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
            '<title>정상연 — 포트폴리오 요약</title>'
            '<link rel="stylesheet" href="assets/font/pretendard.css">'
            '<style>%s</style></head><body>%s</body></html>' % (css, body))
    html = shrink(html)
    src = os.path.join(ROOT, '_summary.html')
    io.open(src, 'w', encoding='utf-8', newline='').write(html)
    print('  조판 %d쪽' % len(pages))
    size, pg = pdfkit.print_pdf(src, os.path.join(OUT, PDF), expect=len(pages))
    print('  %s  %.1fMB  %d쪽' % (PDF, size / 1048576.0, pg))
    return 0


if __name__ == '__main__':
    sys.exit(main())
