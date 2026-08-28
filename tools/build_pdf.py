# -*- coding: utf-8 -*-
"""제출용 포트폴리오 PDF를 조판한다.

인쇄기에 흐름을 맡기면 카드 한가운데가 잘린다. 그래서 쪼갤 수 없는
덩어리로 먼저 나누고, 헤드리스 크롬으로 높이를 실측한 뒤, 한 쪽씩
직접 담는다(tools/pdfkit.py). 잘릴 자리가 없다.

구성은 캡처 나열이 아니라 장(章)으로 짠다.
  표지 → 목차 → 프로필 → 스킬 → 자격증·수상·교육
  → 01 COGI (장 표지 · 개요 · 실제 화면 · 상세)
  → 02 TripLinker → 03 오몽 → 04 더 많은 작업 → 링크

디자인은 사이트 CSS를 그대로 쓴다. 상세페이지 CSS는 메인과 34개
셀렉터가 겹치므로 .det 아래로 가둔 뒤 합친다.

사용 — python tools/build_pdf.py
"""
import io
import json
import os
import re
import shutil
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pdfkit
import pdfdoc
import pdfpages
from pdfkit import Block, split_top, inner

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')

MAIN_PDF = '포트폴리오_정상연_최종.pdf'
DOCS_PDF = '포트폴리오_정상연_산출물.pdf'
SITE = 'https://ynkite.github.io/portfolio/'
DOCS_URL = ('https://ynkite.github.io/portfolio/assets/'
            '%ED%8F%AC%ED%8A%B8%ED%8F%B4%EB%A6%AC%EC%98%A4_'
            '%EC%A0%95%EC%83%81%EC%97%B0_%EC%82%B0%EC%B6%9C%EB%AC%BC.pdf')

IMGDIR = '_pdfimg'
IMGMAX = 1100   # 지면에서 차지하는 폭의 두 배. 확대해도 읽히고 파일은 가볍다

CHAPTERS = [
    dict(no='01', sec='work', file='projects/cogi.html', name='COGI', brand='#1c4f8c'),
    dict(no='02', sec='triplinker', file='projects/triplinker.html', name='TripLinker', brand='#a85c28'),
    dict(no='03', sec='omong', file='projects/omong.html', name='오몽', brand='#E07B1E'),
]

SHOTS = {
    'work': ('pfwide', [
        ('cogi-01-dashboard.png',       '대시보드 — 학습일 · 크레딧 · 약점 집계'),
        ('cogi-04-review.png',          'AI 리뷰 결과'),
        ('cogi-06-learning-card.png',   '학습 카드 — 개념 · 예제 · 퀴즈'),
        ('cogi-07-skill-recommend.png', 'AI 스킬 추천'),
        ('cogi-08-weekly-report.png',   '주간 리포트 메일'),
        ('cogi-02-retention.png',       '리텐션 — streak와 코기 상태'),
    ]),
    'triplinker': ('pfwide', [
        ('tl-02-plan-basic.png', '플랜 만들기 — 기본 정보'),
        ('tl-03-plan-taste.png', '플랜 만들기 — 취향 설정'),
        ('tl-05-day1.jpg',       '1일차 경로 — 지도와 순서'),
        ('tl-07-reorder.jpg',    '장소 순서 교체 결과'),
        ('tl-09-chat.png',       'AI 챗봇 — 플랜 수정 요청'),
        ('tl-11-ledger.png',     '가계부 — 지출 내역'),
    ]),
    'omong': ('pfphone', [
        ('omong-01-home.png',    '홈 — 말하기 · 사진 · 제보'),
        ('omong-04-narrow.png',  'AI 대화로 메뉴 좁히기'),
        ('omong-06-guide2.png',  '화면 안내 — 메뉴 위치 짚어주기'),
        ('omong-08-staff.png',   '직원에게 보여주기'),
        ('omong-10-vision.png',  '사진에서 브랜드 인식'),
        ('omong-02-bigtext.png', '같은 화면, 큰글씨 모드'),
    ]),
}

# 프로젝트마다 한 문장 쪽을 둔다. 무엇을 풀었는지 먼저 말하지 않으면
# 뒤의 설계·트러블슈팅이 그냥 목록으로 읽힌다
STATEMENT = {
    'work': ('리뷰에서 지적받은 걸<br>다음 리뷰에서 또 지적받는다.',
             '반복된 지적을 약점으로 모아 학습 카드와 퀴즈로 바꿨습니다.'),
    'triplinker': ('AI가 짠 일정은 그럴듯하지만<br>실제로는 못 가는 동선이 나온다.',
                   '생성은 AI에 맡기고 거리와 순서는 지도 API로 다시 잡았습니다.'),
    'omong': ('키오스크 앞에서 한 번 멈추면<br>뒤에 줄이 선다.',
              '말하거나 찍으면 주문 완료 화면까지 데려다줍니다.'),
}

TILE_SHOTS = {
    'stagepass':  ('sp-01-home.jpg',      '메인 — 추천 공연'),
    'windycamp':  ('wc-03-detail.jpg',    '상품 상세'),
    'deviceshop': ('ds-02-sales.jpg',     '기간별 매출입 현황'),
    'petvillage': ('pv-01-ai-name.jpg',   'AI 이름 추천'),
    'triplan':    ('triplan-01-main.png', '메인 화면'),
    'festa':      ('festa-01-paper.png',  '분석 산출물'),
}


# ────────────────────────────── 읽기 ──────────────────────────────

def read(p):
    return io.open(os.path.join(ROOT, p), encoding='utf-8').read()


def style_of(html):
    return re.search(r'<style>(.*?)</style>', html, re.S).group(1)


def between(s, a, b):
    i = s.index(a)
    return s[i:s.index(b, i)]


def grab(s, opener, tag='div'):
    """opener로 시작하는 요소 하나를 통째로 떼어 온다."""
    i = s.index(opener)
    depth, j = 0, i
    for m in re.finditer(r'<%s\b|</%s>' % (tag, tag), s[i:]):
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                j = i + m.end()
                break
        else:
            depth += 1
    return s[i:j]


def drop(s, opener, tag='div'):
    while opener in s:
        s = s.replace(grab(s, opener, tag), '')
    return s


# ─────────────────────────── CSS 가두기 ───────────────────────────

def _blocks(css):
    out, sel, i = [], '', 0
    while i < len(css):
        c = css[i]
        if c == '{':
            depth, j = 1, i + 1
            while j < len(css) and depth:
                if css[j] == '{':
                    depth += 1
                elif css[j] == '}':
                    depth -= 1
                j += 1
            out.append((sel.strip(), css[i + 1:j - 1]))
            sel, i = '', j
        elif c == '}':
            i += 1
        else:
            sel += c
            i += 1
    return out


def scope(css, pre):
    out = []
    for sel, body in _blocks(css):
        if sel.startswith('@'):
            if sel.startswith(('@media', '@supports')):
                out.append('%s{%s}' % (sel, scope(body, pre)))
            else:
                out.append('%s{%s}' % (sel, body))
            continue
        news = []
        for s in (x.strip() for x in sel.split(',')):
            if not s:
                continue
            if s in ('html', 'body', ':root'):
                news.append(pre)
            elif s == '*':
                news.append(pre + ',' + pre + ' *')
            else:
                for head in ('html ', 'body ', '.js ', 'html.js '):
                    if s.startswith(head):
                        s = s[len(head):]
                        break
                news.append(pre + ' ' + s)
        out.append('%s{%s}' % (','.join(news), body))
    return ''.join(out)


# ────────────────────────── 사진 줄이기 ──────────────────────────

def shrink_images(html):
    """지면 크기에 맞춰 사진을 줄인다. 원본 그대로면 파일이 14MB를 넘는다."""
    out = os.path.join(ROOT, IMGDIR)
    used = sorted(set(re.findall(r'src="(assets/[^"]+\.(?:png|jpg|jpeg))"', html)))
    for rel in used:
        dst = os.path.join(out, rel.replace('assets/', ''))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = Image.open(os.path.join(ROOT, rel))
        keep = any(k in rel for k in ('-erd', '-arch', '-flow'))   # 확대해 읽는 도식
        if im.width > IMGMAX and not keep:
            im = im.resize((IMGMAX, int(round(im.height * IMGMAX / float(im.width)))),
                           Image.LANCZOS)
        if im.mode in ('RGBA', 'LA', 'P'):
            im.save(dst, optimize=True)
        else:
            dst = os.path.splitext(dst)[0] + '.jpg'
            im.convert('RGB').save(dst, quality=84, optimize=True, progressive=True)
        html = html.replace('src="%s"' % rel,
                            'src="%s/%s"' % (IMGDIR, os.path.relpath(dst, out).replace(os.sep, '/')))
    tot = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(out) for f in fs)
    print('  사진 %d장 → %.1fMB' % (len(used), tot / 1048576.0))
    return html


# ─────────────────────────── 표지 · 목차 ───────────────────────────

COVER = '''<div class="cvwrap">
  <div class="cvhead"><span class="cvtag">Portfolio</span><span class="cvyear">2026</span></div>
  <div class="cvname">
    <div>
      <div class="cvrole">Backend Developer · AI Agent Engineer</div>
      <h1>정상연</h1>
      <div class="cvstack">Java · Spring · Spring AI · AWS</div>
    </div>
    <ol class="cvindex">
      <li><b>01</b><span>COGI</span><em>AI 코드리뷰 학습 플랫폼</em></li>
      <li><b>02</b><span>TripLinker</span><em>AI 여행 플래너</em></li>
      <li><b>03</b><span>오몽</span><em>키오스크 주문 도우미</em></li>
      <li><b>04</b><span>더 많은 작업</span><em>개인 프로젝트 6건</em></li>
    </ol>
  </div>
  <div class="cvfoot">
    <p class="cvlead">GitHub PR을 AI가 리뷰하는 학습 플랫폼, AI가 짠 일정을 카카오 지도로 보정하는 여행 플래너,
      키오스크 앞에서 말로 주문을 돕는 서비스를 만들었습니다.<br>세 프로젝트 모두 AWS 배포까지 마쳤고 두 곳에서 팀장을 맡았습니다.
      <br><b>직접 만든 평가셋 440문항으로 재고, 고친 다음 같은 평가셋을 한 번 더 돌렸습니다.</b></p>
    <dl class="cvmeta">
      <div><dt>웹</dt><dd><a href="{site}">ynkite.github.io/portfolio</a></dd></div>
      <div><dt>메일</dt><dd>j.sangyeon6@gmail.com</dd></div>
      <div><dt>전화</dt><dd>010-4211-3521</dd></div>
      <div><dt>깃허브</dt><dd>github.com/ynkite</dd></div>
    </dl>
  </div>
</div>'''

TOC_ROWS = [
    ('프로필', '이름 · 학력 · 교육 · 경력 · 연락처'),
    ('스킬', 'Backend · AI · DB · Infra · Frontend'),
    ('자격증 · 수상 · 교육', '자격증 5 · 경진대회 8 · KDT 1024h'),
    ('01 COGI', 'AI 코드리뷰 학습 플랫폼 — 평가셋 138문항 · 실제 화면 6장'),
    ('02 TripLinker', 'AI 여행 플래너 — 평가셋 250문항 · 실제 화면 6장'),
    ('03 오몽', '키오스크 주문 도우미 — 평가셋 52문항 · 실제 화면 6장'),
    ('04 더 많은 작업', 'StagePass · WindyCamp · DEVICE SHOP · PetVillage · Triplan · Analyze Festa'),
    ('링크 · 연락처', '010-4211-3521 · j.sangyeon6@gmail.com'),
]


def toc_html():
    rows = ''.join(
        '<li><b>%s</b><span>%s</span></li>' % (t, d) for t, d in TOC_ROWS)
    return '''<div class="tocwrap">
  <div class="tochd"><span class="kick">Contents</span><h2>목차</h2></div>
  <div class="tocgrid">
    <ol class="toclist">%s</ol>
    <aside class="tocside">
      <div class="tsblk"><b>440문항</b><span>세 프로젝트에 쓴<br>직접 만든 평가셋</span></div>
      <div class="tsblk"><b>3</b><span>팀 프로젝트<br>전부 AWS 배포</span></div>
      <div class="tsblk"><b>1024h</b><span>대우능력개발원<br>KDT 이수</span></div>
      <div class="tsblk"><b>8회</b><span>교내외<br>경진대회 수상</span></div>
    </aside>
  </div>
</div>''' % rows


# 장마다 대표 수치 세 개. 지면에 근거가 있는 값만 쓴다
CHSTATS = {'work': [('138문항', '직접 만든 평가셋'), ('100%', '카드 생성 성공 (68/68)'), ('180건', '테스트 케이스 · 96% 통과')], 'triplinker': [('250문항', '직접 만든 평가셋'), ('11.4% → 100%', '장소 실재율 · 모델 단독 대비'), ('41% → 100%', '일정 생성률 · 세 회차')], 'omong': [('52장', '키오스크 사진 평가셋'), ('100%', '스키마 준수 · 규칙 폴백 응답'), ('2박 3일', '해커톤 · 아이디어상 · 팀 MVP')]}

# 장마다 실제 절 순서
CHTOC = {'work': '개요 · 실제 화면 · 분석 · 설계 · 주요 기능 · 담당 파트 · 개발과 평가 · 배포 및 테스트', 'triplinker': '개요 · 실제 화면 · 분석 · 설계 · 주요 기능 · 담당 파트 · 개발과 평가 · 배포 및 테스트', 'omong': '개요 · 실제 화면 · 분석 · 설계 · 주요 기능 · 담당 파트 · 개발과 평가 · 배포 및 테스트 · 언론 보도'}

CH_TOC = '개요 · 실제 화면 · 분석 · 설계 · 개발 · 배포와 테스트 · 담당 파트 · 트러블슈팅 · 주요 기능'

# 실제로 들어가서 눌러 볼 수 있게 열어 둔 계정. 오몽은 로그인이 없어 넣지 않는다.
DEMO = {
    'work': ('user@a.a', '1234', ''),
    'triplinker': ('user01', '1234',
                   '챗봇 대화까지 되고, 일정은 미리 넣어 둔 것이 뜹니다'),
}


def chapter_html(no, name, brand, kick, desc, meta, chips, links, toc=CH_TOC, stats=None,
                 demo=None):
    """장 표지. 제목은 위, 기간·기술·링크는 아래 가로대에 세 칸으로 세운다.

    알약 칩을 흘려 두면 줄이 들쭉날쭉하게 접히고, 버튼을 가운데 두면
    지면이 슬라이드처럼 보인다. 활자로 가르고 왼쪽에 맞춘다.
    """
    stack = ' · '.join(re.findall(r'<span[^>]*>(.*?)</span>', chips)) if chips else ''
    cells = []
    if meta:
        bits = [x.strip() for x in re.split(r'\s*\|\s*', re.sub(r'<[^>]+>', '', meta)) if x.strip()]
        # 칸이 좁으면 줄로 쌓고, 가로대를 혼자 쓰면 한 줄로 편다
        cells.append(('기간 · 팀', (' · ' if not (stack or links) else '<br>').join(bits)))
    if stack:
        cells.append(('기술', stack))
    rail = ''.join('<div class="chcell"><b>%s</b><span>%s</span></div>' % kv for kv in cells)
    n = len(cells)
    if links:
        rail += '<div class="chcell chlinks"><b>링크</b>%s</div>' % links
        n += 1

    # 칸 수는 장마다 다르다. 세 칸으로 못 박으면 기술·링크가 없는 장에서
    # 오른쪽 두 칸이 빈 채로 남아 가로대가 한쪽으로 쏠린다
    cols = {1: '1fr', 2: '240px 1fr'}.get(n, '190px 1fr 220px')
    rail = '<div class="chrail" style="grid-template-columns:%s">%s</div>' % (cols, rail)
    if demo:
        note = ('<i>%s</i>' % demo[2]) if demo[2] else ''
        rail += ('<div class="chdemo"><b>테스트 계정</b>'
                 '<span><u>%s</u> / <u>%s</u></span>%s</div>'
                 % (demo[0], demo[1], note))
    box = ''
    if stats:
        cells = ''.join('<div class="chstat"><b>%s</b><span>%s</span></div>' % kv for kv in stats)
        box = '<div class="chstats">%s</div>' % cells
    return ('<div class="det chapwrap" style="--brand:%s"><div class="chap">'
            '<div class="chno">%s</div>'
            '<div class="chbody"><div class="chkick">%s</div><h2>%s</h2>'
            '<div class="chdesc">%s</div></div></div>%s%s'
            '<div class="chtoc"><b>이 장의 구성</b><span>%s</span></div></div>'
            % (brand, no, kick, name, desc, box, rail, toc))


# ─────────────────────────── 블록 만들기 ───────────────────────────

def figures(shots, kind, per):
    """사진을 한 줄씩 블록으로 낸다. 줄 단위라 쪽 경계에서 잘리지 않는다."""
    out = []
    for i in range(0, len(shots), per):
        cells = ''.join(
            '<figure class="pf"><img src="assets/image/%s" alt="%s">'
            '<figcaption>%s</figcaption></figure>' % (f, c, c)
            for f, c in shots[i:i + per])
        out.append('<div class="pfgrid %s">%s</div>' % (kind, cells))
    return out


CHUNK = {'cards': 2, 'dtable': 4, 'feats': 4, 'parts': 2, 'press': 3, 'ts': 1}


def chunk_grid(el, per):
    """격자 안 자식들을 per개씩 묶어 여러 블록으로 낸다. 쪽 경계에서 안 잘린다."""
    open_tag = el[:el.index('>') + 1]
    kids = split_top(inner(el))
    return [open_tag + ''.join(kids[i:i + per]) + '</div>'
            for i in range(0, len(kids), per)]


def maybe_chunk(el):
    """클래스 목록을 제대로 훑는다. class="cards rv d1" 처럼 붙어 오기 때문이다."""
    open_tag = el[:el.index('>') + 1]
    m = re.search(r'class="([^"]*)"', open_tag)
    if m:
        for c in m.group(1).split():
            if c in CHUNK:
                return chunk_grid(el, CHUNK[c])
    return [el]


DOC_KEYS = ('req', 'func', 'wbs', 'api')
DOC_JS = {'work': 'cogi', 'triplinker': 'tl', 'omong': 'om'}


def docs_page(sec, brand, tag, head=None):
    """산출물 네 종을 한 쪽에 4분할로 싣는다.

    읽히라고 넣는 지면이 아니다. 이런 문서를 실제로 썼다는 것만 보이면 된다.
    그래서 글자는 작게 두고 넘치는 부분은 지면에서 잘라 낸다.
    전문은 별첨 PDF에 있다.
    """
    d = pdfdoc.docsets(DOC_JS[sec])
    sheets = ''
    for k in DOC_KEYS:
        s = d.get(k)
        if not s:
            continue
        thead = ''.join('<th>%s</th>' % esc(h) for h in s['head'])   # 인자 head 와 겹치지 않게
        n = len(s['head'])
        body = ''
        # 행은 세 가지 꼴이다 — 칸 목록, 색을 입힌 {'c': [...]}, 묶음 제목 {'g': ...}.
        # 그대로 훑으면 키 이름만 찍혀 빈 표로 보인다
        for r in s['rows'][:22]:
            if isinstance(r, dict) and 'g' in r:
                body += '<tr><td class="dpg" colspan="%d">%s</td></tr>' % (n, esc(r['g']))
                continue
            cs = r['c'] if isinstance(r, dict) else r
            body += '<tr>%s</tr>' % ''.join('<td>%s</td>' % esc(c) for c in cs)
        sheets += ('<div class="dpcell"><div class="dphd"><b>%s</b>'
                   '<span>%d행</span></div><div class="dpsheet">'
                   '<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>'
                   '</div></div>' % (esc(s['label']), len(s['rows']), thead, body))
    return ('<div class="det fillblk dpage" style="--brand:%s">%s'
            '<div class="dpgrid">%s</div></div>'
            % (brand,
               head or sechd('DOCUMENTS', '산출물',
                             '요구사항 정의서 · 기능 정의서 · WBS · API 명세서를 직접 작성했습니다.<br>'
                             '전문은 별첨 「포트폴리오_정상연_산출물.pdf」에 실었습니다.'),
               sheets))


def shot_dims(shots):
    """화면 사진의 원래 크기. 자르지 않고 지면에 앉히려면 비율을 알아야 한다."""
    out = {}
    for f, _ in shots:
        with Image.open(os.path.join(ROOT, 'assets', 'image', f)) as im:
            out[f] = im.size
    return out


def wrap_det(html, brand):
    return '<div class="det" style="--brand:%s"><div class="wrap">%s</div></div>' % (brand, html)


# 절이 끝났다는 신호. 쉼표는 이 어미 뒤에 올 때만 줄을 넘긴다.
# 모든 쉼표에서 넘기면 "인증·보안, AI 일정 생성, 경로·동선," 같은 나열이
# 낱줄로 흩어진다
CONNECT = re.compile(r'(?:고|며|면서|지만|는데|아서|어서|해서|하여|되어|따라)\s*,\s+(?=\S)')


def brk(html):
    """뜻이 끝나는 자리에서만 줄을 넘긴다.

    폭에 맡기면 "…학습 카드와 퀴즈로 / 만들어 주는 서비스입니다" 처럼
    문장 한가운데가 끊긴다. 마침표 뒤와 연결 어미 뒤에서만 넘긴다.
    """
    if not html:
        return html
    s = re.sub(r'<br\s*/?>', ' ', html)          # 사이트가 박아 둔 줄바꿈은 걷는다
    s = re.sub(r'\s+', ' ', s).strip()
    # 숫자 사이 마침표(43.202.36.123)는 뒤에 공백이 없으므로 걸리지 않는다
    s = re.sub(r'(?<=\.)\s+(?=\S)', '<br>', s)
    return CONNECT.sub(lambda m: m.group(0).rstrip()[:-1] + ',<br>', s)


def clauses(html):
    """쉼표·마침표를 경계로 조각내 각 조각을 한 덩어리로 묶는다.

    줄이 넘칠 때 브라우저가 조각 사이에서만 끊으므로 줄 끝이 늘 `,` 나 `.` 이
    된다. 한 조각이 줄보다 길면 그 안에서 접히니 넘쳐 잘릴 일은 없다.
    태그 밖 글자만 자른다 — <code> 안이나 속성값을 건드리면 마크업이 깨진다.
    """
    if not html or '<' == html.strip()[:1] and '>' not in html:
        return html
    out, buf, depth, i = [], '', 0, 0
    while i < len(html):
        c = html[i]
        if c == '<':
            depth += 1
        elif c == '>':
            depth -= 1
        buf += c
        if depth == 0 and c in ',.' and i + 1 < len(html) and html[i + 1] == ' ':
            out.append(buf)
            buf = ''
            i += 1          # 조각 사이 공백은 버린다. inline-block 이 간격을 만든다
        i += 1
    if buf:
        out.append(buf)
    if len(out) < 2:
        return html
    return ' '.join('<span class="cl">%s</span>' % x.strip() for x in out if x.strip())


def run_head(sec):
    return (sec['step'], sec['title'])


def sechd(step, title, lead):
    return ('<div class="sechd"><div><div class="step">%s</div>'
            '<h2 class="stitle">%s</h2></div>'
            '<div class="sectxt"><p class="lead">%s</p></div></div>' % (step, title, lead))


# ─────────────────── 프로필 · 스킬 · 자격증 지면 ───────────────────

def profile_page(lead):
    """이름·연락처를 왼쪽 기둥에, 이력을 오른쪽 표에 세운다.

    사이트의 3×3 표를 그대로 옮기면 지면에서 서식 문서로 읽힌다.
    값은 그대로 두고 지면 구조만 새로 짠다.
    """
    p = pdfdoc.profile()
    name = p.get('이름', '')
    kr = name.split('(')[0].strip()
    en = name[name.find('(') + 1:name.rfind(')')].strip() if '(' in name else ''
    parts = [x.strip() for x in p.get('연락처', '').split('·')]
    mail = next((x for x in parts if '@' in x), '')
    tel = next((x for x in parts if '@' not in x), '')
    contact = [('메일', mail), ('전화', tel),
               ('깃허브', p.get('GitHub', '')), ('블로그', p.get('기술 블로그', ''))]
    rows = [('학력', p.get('학력', '')),
            ('교육', p.get('교육', '')),
            ('경력', p.get('경력', '')),
            ('자격 · 수상', p.get('자격증 · 수상', '')),
            ('주력 스킬', p.get('스킬', '')),
            ('대표 프로젝트', p.get('대표 프로젝트', ''))]
    return ('<div class="fillblk pfpage">'
            '<div class="pfid">''<div class="pfphoto"><img src="assets/profile.jpg" alt="정상연"></div>''<div class="pfrole">Backend Developer · AI Agent Engineer</div>'
            '<h2 class="pfname">%s</h2><div class="pfen">%s · %s</div>'
            '<dl class="pfct">%s</dl></div>'
            '<div class="pfbody"><div class="step">PROFILE</div>'
            '<h2 class="stitle">프로필</h2><p class="pflead">%s</p>'
            '<div class="pftable">%s</div></div></div>'
            % (kr, en, p.get('생년월일', ''),
               ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % kv for kv in contact),
               lead,
               ''.join('<div class="pfr"><b>%s</b><span>%s</span></div>' % kv for kv in rows)))


def skills_page():
    """분류를 왼쪽 기둥에 세우고 이름만 늘어놓는다. 설명은 싣지 않는다."""
    cats, _ = pdfdoc.skills()
    rows = ''
    for c in cats:
        groups = ''
        for cls, tag in (('smcore', 'smk'), ('smrest', 'smn')):
            names = ''.join('<span class="%s">%s</span>' % (tag, n)
                            for _, n, k in c['items'] if k == (tag == 'smk'))
            if names:   # 주력이 없는 분류에 빈 줄을 남기면 이름이 아래로 쏠린다
                groups += '<div class="%s">%s</div>' % (cls, names)
        rows += ('<div class="smrow"><div class="smcat">%s</div>'
                 '<div class="smlist">%s</div></div>' % (c['name'], groups))
    return ('<div class="fillblk skpage">%s<div class="skmatrix">%s</div></div>'
            % (sechd('SKILLS', '스킬',
                     ''),
               rows))


def cr_rows(rows):
    return ''.join(
        '<div class="crrow"><div class="crn"><b>%s</b><em>%s</em></div>'
        '<div class="crv">%s<span>%s</span></div></div>'
        % (r['nm'], r['sub'], '<i>%s</i>' % r['tag'] if r['tag'] else '', r['val'])
        for r in rows)


def credits_pages():
    """자격증·수상은 한 쪽에 나란히, 교육은 두 단으로. 접힌 상자를 걷어 낸다."""
    cr = pdfdoc.credits()
    lic, awd, edu = cr[0], cr[1], cr[2]
    col = ('<div class="crcol"><div class="crhd"><b>%s</b><span>%s</span></div>'
           '%s<p class="crnote">%s</p></div>')
    page1 = ('<div class="fillblk crpage">%s<div class="crgrid">%s%s</div></div>'
             % (sechd('CREDITS', '자격증 · 수상',
                      '자격증 5건을 취득했고, 교내외 경진대회에서 8회 수상했습니다.'),
                col % (lic['title'], lic['sub'], cr_rows(lic['rows']), lic['note']),
                col % (awd['title'], awd['sub'], cr_rows(awd['rows']), awd['note'])))
    half = (len(edu['rows']) + 1) // 2
    page2 = ('<div class="fillblk crpage">%s'
             '<div class="crhd"><b>%s</b><span>%s</span></div>'
             '<div class="edugrid"><div>%s</div><div>%s</div></div>'
             '<p class="crnote">%s</p></div>'
             % (sechd('EDUCATION', '교육',
                      '대우능력개발원 KDT 과정에서 1024시간을 이수했습니다.'),
                edu['title'], edu['sub'],
                cr_rows(edu['rows'][:half]), cr_rows(edu['rows'][half:]), edu['note']))
    return [page1, page2]


def build_blocks():
    """지면용 쪽들을 짠다. 쪽마다 담을 개수를 정해 두어 어중간하게 비지 않는다."""
    ix = pdfdoc.index_parts()
    B = []

    B.append(Block(COVER.replace('{site}', SITE), newpage=True))
    B.append(Block(toc_html(), newpage=True, tag='목차'))

    B.append(Block(profile_page(ix['lead']), newpage=True, tag='프로필',
                   fixh=pdfkit.BODY_H))
    B.append(Block(skills_page(), newpage=True, tag='스킬', fixh=pdfkit.BODY_H))
    for html in credits_pages():
        B.append(Block(html, newpage=True, tag='자격증 · 수상', fixh=pdfkit.BODY_H))

    # ── 프로젝트 세 장
    for ch in CHAPTERS:
        pj = pdfdoc.project(ch['file'])
        brand, tag = ch['brand'], ch['name']
        B.append(Block(chapter_html(ch['no'], pj['name'], brand, pj['kick'], pj['desc'],
                                    pj['meta'], pj['chips'], pj['links'],
                                    toc=CHTOC.get(ch['sec'], CH_TOC),
                                    stats=CHSTATS.get(ch['sec']),
                                    demo=DEMO.get(ch['sec'])),
                       newpage=True, tag=tag))

        # 개요 : 왼쪽 글과 지표, 오른쪽 목업
        ov = pj['sections'][0]
        ovhtml = next((b['html'] for b in ov['blocks'] if b['t'] == 'ov'), '')
        feat = ix['feat'][ch['sec']]
        B.append(Block(
            '<div class="ovpage">'
            '<div class="ovtext"><div class="step">OVERVIEW</div>'
            '<h2 class="stitle">개요</h2>'
            '<div class="rline">%s</div><p class="lead">%s</p>%s%s</div>'
            '<div class="ovshot">%s</div></div>'
            % (ov['rline'], brk(ov['lead']), det_only(ovhtml, brand), feat['bullets'],
               feat['device']),
            newpage=True, tag=tag))

        # 화면은 한 쪽을 통째로 쓴다. 대표 한 장만 크게 싣고 나머지를 작게
        # 늘어놓으면 나머지가 안 읽힌다. 전부 같은 크기로 크게 싣는다
        kind, shots = SHOTS[ch['sec']]
        B += pdfpages.shot_pages(kind, shots, brand, tag, pdfkit.BODY_H, shot_dims(shots))

        for si, sec in enumerate(pj['sections'][1:]):
            secb = pdfpages.section_pages(sec, brand, tag,
                                          grp='%s-%d' % (ch['sec'], si), brk=clauses,
                                          budget=pdfkit.BODY_H)
            # 분석 바로 뒤에 산출물 미리보기 한 쪽.
            # 분석에 실을 블록이 없으면 절 머리만 있는 빈 쪽이 생기므로
            # 산출물을 그 쪽에 얹어 한 쪽으로 합친다
            if sec['step'].endswith('ANALYSIS'):
                if not [b for b in sec['blocks'] if b['t'] != 'docs']:
                    B.append(Block(
                        docs_page(ch['sec'], brand, tag,
                                  head=pdfpages.sec_head(sec['step'], sec['title'],
                                                         sec['lead'], sec['rline'])),
                        newpage=True, tag=tag, fixh=pdfkit.BODY_H, head=run_head(sec)))
                    continue
                B += secb
                B.append(Block(docs_page(ch['sec'], brand, tag),
                               newpage=True, tag=tag, fixh=pdfkit.BODY_H,
                               head=('DOCUMENTS', '산출물')))
                continue
            B += secb

    # ── 더 많은 작업 : 한 쪽에 둘씩
    B.append(Block(chapter_html('04', '더 많은 작업', '#2b2b30', 'More Work',
                                '경진대회와 수업에서 만든 여섯 개입니다.<br>모두 혼자 설계하고 구현했습니다.',
                                '2024.11 – 2026.06 | 개인 프로젝트 6건 | 수상 4건', '', '',
                                'StagePass · WindyCamp · DEVICE SHOP · PetVillage · Triplan · Analyze Festa'),
                   newpage=True, tag='더 많은 작업'))
    tiles = []
    for el in ix['tiles']:
        m = re.search(r'data-lb="(\w+)"', el)
        if m and m.group(1) in TILE_SHOTS:
            f, cap = TILE_SHOTS[m.group(1)]
            fig = ('<figure class="pf tilepf"><img src="assets/image/%s" alt="%s">'
                   '<figcaption>%s</figcaption></figure>' % (f, cap, cap))
            el = el.replace('<div class="tbtns">', fig + '<div class="tbtns">')
        tiles.append(el)
    for part in pdfpages.chunk(tiles, 2):
        B.append(Block('<div class="tiles pairtile">%s</div>' % ''.join(part),
                       newpage=True, tag='더 많은 작업', head=('MORE WORK', '더 많은 작업')))

    # ── 링크
    B.append(Block(
        '<div class="sechd"><div><div class="step">LINK</div>'
        '<h2 class="stitle">링크 · 연락처</h2></div>'
        '<div class="sectxt"><p class="lead">소스와 커밋 기록은 GitHub에, 트러블슈팅은 블로그에 정리했습니다.'
        '<br>채용 문의는 메일이 가장 빠릅니다.</p></div></div>',
        newpage=True, keepnext=True, tag='링크'))
    # 이모지는 화면에서는 살지만 인쇄하면 컬러 비트맵으로 박혀
    # 흑백 편집 지면에서 혼자 떠 보인다. 활자로만 세운다
    B.append(Block(re.sub(r'<span class="ic">.*?</span>', '', ix['archcards']),
                   tag='링크', head=('LINK', '링크 · 연락처')))

    for b in B:
        b.html = re.sub(r'<button class="(?:pbtn|tbtn)"[^>]*data-lb="[^"]*"[^>]*>.*?</button>',
                        '', b.html, flags=re.S)
        b.html = re.sub(r'<a class="pbtn dark" href="\./projects/[^"]*">.*?</a>', '', b.html, flags=re.S)
        b.html = b.html.replace('href="./projects/', 'href="' + SITE + 'projects/')
        b.html = b.html.replace(' snap"', '"').replace(' snap ', ' ')
        b.html = b.html.replace('../assets/', 'assets/')
    return B


def det_only(html, brand):
    return '<div class="det" style="--brand:%s">%s</div>' % (brand, html) if html else ''


# ─────────────────────────── 인쇄 CSS ───────────────────────────

PRINT_CSS = '''
html, body { overflow: hidden }

@page { size: 297mm 210mm; margin: 0 }
html, body { background: #fff; margin: 0 }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact }

.page { position: relative; width: 296.9mm; height: 209.6mm; overflow: hidden;
  box-sizing: border-box; padding: 82px 64px 60px; background: #fff;
  break-after: page; break-inside: avoid }
.page:last-child { break-after: auto }
.page.bleed { padding: 0 }
/* 본문 상자에 조판 예산만큼 높이를 준다. 이래야 지면을 채우는 블록이
   남은 자리를 정확히 알아 아래가 텅 비지 않는다 */
.pgbody { display: flex; flex-direction: column; height: __BODYH__px }
.pgbody > * { flex: none }
/* 지면을 채우는 블록. display 는 건드리지 않는다 — 여기서 flex 를 박으면
   .pfpage 같은 격자 지면이 특정도에 밀려 통째로 무너진다 */
.pgbody > .fillblk { flex: 1 1 auto; min-height: 0 }
.pgbody > .det.fillblk { display: flex; flex-direction: column }

/* 이어지는 쪽 머리 — 여기가 어느 절인지 한 줄로 알린다 */
.runhd { position: absolute; top: 46px; left: 64px; right: 64px;
  display: flex; gap: 14px; align-items: baseline;
  border-bottom: 1px solid var(--line); padding-bottom: 9px }
.runhd .step { font-size: 10px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--brand, var(--muted)); font-weight: 700 }
.runhd span:nth-child(2) { font-size: 12.5px; font-weight: 650;
  letter-spacing: -.012em; color: var(--sub) }

/* 바닥글 — 어디에 있는지 늘 답한다 (§16 길찾기) */
.pfoot { position: absolute; left: 64px; right: 64px; bottom: 24px;
  display: flex; gap: 16px; align-items: baseline;
  border-top: 1px solid var(--line); padding-top: 10px;
  font-size: 10px; letter-spacing: .08em; color: var(--muted) }
.pfoot span:nth-child(2) { color: var(--brand, var(--sub)); font-weight: 700; letter-spacing: .04em }
.pfoot span:last-child { margin-left: auto; font-variant-numeric: tabular-nums; letter-spacing: .04em }

/* 크기별 자간·행간 (§15). 큰 글자는 좁히고 작은 글자는 벌린다 */
.pdfdoc h1 { letter-spacing: -.058em; line-height: .94 }
.pdfdoc h2 { letter-spacing: -.045em; line-height: 1.04 }
.pdfdoc h3 { letter-spacing: -.022em; line-height: 1.2 }
.pdfdoc h4 { letter-spacing: -.015em; line-height: 1.38 }
.pdfdoc p, .pdfdoc li { letter-spacing: 0 }
.pdfdoc .step, .pdfdoc .kick, .pdfdoc .cvtag { letter-spacing: .2em }
.pdfdoc figcaption, .pdfdoc .cap { letter-spacing: .012em }

/* 화면에서만 쓰는 장치를 꺼 둔다 */
.pdfdoc .rv, .pdfdoc .det .rv { opacity: 1 !important; transform: none !important; animation: none !important }
.pdfdoc .skpanel, .pdfdoc .skp { display: block !important; visibility: visible !important;
  opacity: 1 !important; grid-area: auto !important }
.pdfdoc .sk { pointer-events: none }
.pdfdoc .fold > summary { list-style: none; cursor: default }
.pdfdoc .fold .more { display: none }
.pdfdoc .wrap { max-width: none !important; margin: 0 !important; padding: 0 !important }
.pdfdoc { --mockh: 320px }
.pdfdoc .device.duo { width: auto !important; gap: 26px }
.pdfdoc .browser { max-width: 496px !important }
.pdfdoc .mockimg { max-width: 150px !important }
.pdfdoc .foot { display: none }
.pdfdoc .page section { padding: 0 !important; min-height: 0 !important }
.pdfdoc .shead { margin-bottom: 22px }
.pdfdoc .mblk + .mblk { margin-top: 0 }

/* 표지 — 가운데 정렬 대신 편집 지면처럼 좌하단에 무게를 둔다 */
.cvwrap { height: 100%; box-sizing: border-box; padding: 62px 72px 66px;
  display: grid; grid-template-rows: auto 1fr auto;
  background: linear-gradient(180deg, #fbfbfc 0%, #fff 42%) }
.cvhead { display: flex; align-items: baseline; gap: 14px;
  font-size: 11px; letter-spacing: .22em; text-transform: uppercase; color: var(--muted) }
.cvhead .cvyear { margin-left: auto; font-variant-numeric: tabular-nums }
.cvhead { border-bottom: 1px solid var(--line); padding-bottom: 14px }
.cvname { align-self: center; padding-left: 2px;
  display: grid; grid-template-columns: 1.35fr 1fr; gap: 56px; align-items: end }
.cvindex { list-style: none; margin: 0; padding: 0 0 0 34px; border-left: 1px solid var(--line) }
.cvindex li { display: grid; grid-template-columns: 30px 1fr; gap: 4px 12px;
  padding: 10px 0; border-bottom: 1px solid var(--line) }
.cvindex li:last-child { border-bottom: 0 }
.cvindex b { font-size: 11px; color: var(--muted); font-variant-numeric: tabular-nums;
  letter-spacing: .04em; padding-top: 3px }
.cvindex span { font-size: 15.5px; font-weight: 650; letter-spacing: -.015em }
.cvindex em { grid-column: 2; font-style: normal; font-size: 12px; color: var(--muted) }
.cvname .cvrole { font-size: 15px; font-weight: 650; letter-spacing: .02em; color: var(--blue) }
.cvname h1 { font-size: 108px; line-height: .92; letter-spacing: -.058em; margin: 10px 0 14px }
.cvname .cvstack { font-size: 25px; font-weight: 600; letter-spacing: -.02em; color: var(--sub) }
.cvfoot { display: grid; grid-template-columns: 1.55fr 1fr; gap: 46px; align-items: end;
  border-top: 1px solid var(--line); padding-top: 26px }
.cvlead { font-size: 14.5px; line-height: 1.78; color: var(--sub); letter-spacing: .005em }
.cvmeta { display: grid; gap: 7px; font-size: 13px }
.cvmeta > div { display: flex; gap: 12px }
.cvmeta dt { width: 46px; flex: none; color: var(--muted); font-size: 11.5px; letter-spacing: .06em }
.cvmeta dd { margin: 0; color: var(--sub); font-weight: 550 }
.cvmeta a { color: var(--blue); font-weight: 650 }

/* 목차 */
.tochd { margin-bottom: 20px }
.tochd .kick { display: block; font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 8px }
.tochd h2 { font-size: 40px; letter-spacing: -.04em; line-height: 1 }
.tocgrid { display: grid; grid-template-columns: 1.7fr 1fr; gap: 54px }
.toclist { list-style: none; counter-reset: t; margin: 0; padding: 0 }
.toclist li { counter-increment: t; padding: 8px 0; border-bottom: 1px solid var(--line) }
.toclist li::before { content: counter(t, decimal-leading-zero); font-size: 11px; font-weight: 700;
  color: var(--muted); font-variant-numeric: tabular-nums; margin-right: 14px }
.toclist b { font-size: 16.5px; font-weight: 650; letter-spacing: -.012em }
.toclist span { display: block; margin: 4px 0 0 32px; font-size: 12.5px; color: var(--muted) }
.tocside { border-left: 1px solid var(--line); padding-left: 34px }
.tsblk { padding: 10px 0; border-bottom: 1px solid var(--line) }
.tsblk b { display: block; font-size: 27px; font-weight: 700; letter-spacing: -.04em;
  font-variant-numeric: tabular-nums; line-height: 1 }
.tsblk span { display: block; margin-top: 5px; font-size: 12px; line-height: 1.5; color: var(--muted) }
.tsnote { margin-top: 18px; font-size: 11.5px; line-height: 1.65; color: var(--muted) }
.tsnote a { color: var(--blue); text-decoration: underline; text-underline-offset: 3px }

/* 장 표지 */
/* 조판 예산(pdfkit.BODY_H)보다 커지면 통째로 축소돼 활자 크기가 어긋난다.
   한 칸 아래로 잡아 둔다 */
.chapwrap { min-height: 628px; display: flex; flex-direction: column }
.chap { display: grid; grid-template-columns: 168px 1fr; gap: 8px; align-items: start;
  padding-top: 26px }
/* 링크 버튼이 아래 괘선에 붙지 않게 숨을 둔다 */
/* 장 표지 대표 수치 — 문패와 가로대 사이 빈 자리를 메운다 */
.chstats { margin-top: 46px; display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 26px; padding-top: 26px; border-top: 1px solid var(--line) }
.chstat b { display: block; font-size: 40px; font-weight: 700; line-height: 1.02;
  letter-spacing: -.045em; color: var(--brand); font-variant-numeric: tabular-nums }
.chstat span { display: block; margin-top: 9px; font-size: 12.5px; line-height: 1.5;
  color: var(--muted); letter-spacing: -.005em }
.chtoc { margin-top: 30px; padding-top: 18px; border-top: 1px solid var(--line);
  display: flex; gap: 16px; align-items: baseline; font-size: 12.5px; color: var(--muted) }
/* 한글은 자간을 벌리면 "이 장 의 구 성" 처럼 낱자로 흩어진다 */
.chtoc b { font-size: 11px; letter-spacing: .01em; color: var(--brand);
  font-weight: 700; flex: none }
.chno { font-size: 104px; font-weight: 700; line-height: .8; letter-spacing: -.06em;
  color: var(--brand); opacity: .22; font-variant-numeric: tabular-nums }
.chbody { border-left: 1px solid var(--line); padding-left: 40px }
.chkick { font-size: 11px; letter-spacing: .2em; text-transform: uppercase; color: var(--brand);
  font-weight: 700 }
.chbody h2 { font-size: 62px; line-height: 1.02; letter-spacing: -.05em; margin: 12px 0 16px }
.chdesc { font-size: 22px; font-weight: 600; line-height: 1.5; letter-spacing: -.022em; color: var(--sub) }
.chmeta { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--line);
  font-size: 13px; color: var(--muted); letter-spacing: .01em }
.chap .chips { margin-top: 18px }
.chap .links { margin-top: 22px }

/* ── 지면 컴포넌트 ────────────────────────────────────────────
   괘선으로 가르지 않고 부드러운 면으로 묶는다. 여백을 넉넉히 두고
   글자 크기 차이로 위계를 만든다. 테두리와 그림자는 쓰지 않는다 */
.pdfdoc .det .card, .pdfdoc .det .part, .pdfdoc .det .tsitem {
  background: #f5f5f7 !important; border: 0 !important; border-radius: 20px !important;
  padding: 18px 21px !important; box-shadow: none !important }
.pdfdoc .det .cards, .pdfdoc .det .parts { gap: 14px !important; padding: 0 !important }
.pdfdoc .det .card .n, .pdfdoc .det .part .no {
  display: block; font-size: 10.5px; letter-spacing: .16em; text-transform: uppercase;
  color: var(--brand); font-weight: 700; background: none !important; padding: 0 !important;
  margin-bottom: 7px }
.pdfdoc .det .card h4, .pdfdoc .det .part h4 {
  font-size: 16.5px; font-weight: 700; letter-spacing: -.024em; margin-bottom: 7px }
.pdfdoc .det .card p, .pdfdoc .det .part li {
  font-size: 13.2px; line-height: 1.56; color: var(--sub); letter-spacing: -.004em }
.pdfdoc .det .part ul { margin: 0; padding-left: 16px }
/* 줄 끝이 늘 쉼표나 마침표가 되게 조각을 한 덩어리로 묶는다.
   조각 사이에서만 줄이 넘어가고, 조각이 줄보다 길면 그 안에서 접힌다 */
.pdfdoc .cl { display: inline-block }

/* 표 — 상자를 없애고 넓은 줄 간격으로 읽게 한다 */
.pdfdoc .det .dtable { background: none !important; border: 0 !important;
  border-radius: 0 !important; padding: 0 !important; overflow: visible !important }
.pdfdoc .det .drow { background: none !important; border: 0 !important;
  border-top: 1px solid rgba(0,0,0,.08) !important; border-radius: 0 !important;
  padding: 12px 0 !important; box-shadow: none !important }
.pdfdoc .det .drow .k { font-size: 11px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--muted); font-weight: 700 }
.pdfdoc .det .drow .v { font-size: 13.6px; line-height: 1.66; letter-spacing: -.006em }

/* 기능 — 면 하나에 두 줄 */
.pdfdoc .det .feats { gap: 14px !important; padding: 0 !important;
  background: none !important; border: 0 !important }
.pdfdoc .det .feat { background: #f5f5f7 !important; border: 0 !important;
  border-radius: 16px !important; padding: 16px 18px !important; font-size: 13px;
  line-height: 1.6; color: var(--sub) }
.pdfdoc .det .feat b { display: block; font-size: 14.5px; font-weight: 700;
  letter-spacing: -.02em; color: var(--ink); margin-bottom: 4px }

/* 트러블슈팅 — 세 단계를 면으로 나누고 해결에만 색을 얹는다 */
.pdfdoc .det .tsitem .t { font-size: 17px; font-weight: 700; letter-spacing: -.024em;
  margin-bottom: 14px }
.pdfdoc .det .tsflow { gap: 12px !important }
.pdfdoc .det .tsflow .b { background: #fff !important; border: 0 !important;
  border-radius: 14px !important; padding: 14px 16px !important }
.pdfdoc .det .tsflow .b.res { background: color-mix(in srgb, var(--brand) 9%, #fff) !important }
.pdfdoc .det .tsflow .lab { font-size: 10px; letter-spacing: .16em; text-transform: uppercase;
  color: var(--muted); font-weight: 700; background: none !important; padding: 0 !important;
  margin-bottom: 7px }
.pdfdoc .det .tsflow .b.res .lab { color: var(--brand) }
.pdfdoc .det .tsflow p { font-size: 12.8px; line-height: 1.62; color: var(--sub) }

/* 지표 — 숫자를 크게 세우고 상자는 두지 않는다 */
.pdfdoc .det .ov { border: 0 !important; border-radius: 0 !important;
  background: none !important; gap: 0 !important }
.pdfdoc .det .ov .c { padding: 0 !important; border: 0 !important }
.pdfdoc .det .ov b { font-size: 46px; font-weight: 700; letter-spacing: -.05em;
  font-variant-numeric: tabular-nums; line-height: 1 }
.pdfdoc .det .ov span { display: block; margin-top: 8px; font-size: 12px;
  letter-spacing: .02em; color: var(--muted) }

/* 도식과 화면 — 부드러운 바탕 위에 둥근 미디어 */
.pdfdoc .det .figure { border: 0 !important; border-radius: 22px !important;
  background: #f5f5f7 !important; padding: 26px !important }
.pdfdoc .det .figure img { border-radius: 10px }
.pdfdoc .det .figure .cap { margin-top: 16px; font-size: 12px; color: var(--muted);
  padding: 0 !important; border: 0 !important; text-align: center }
.pdfdoc .det .rline { color: var(--brand) }
.pdfdoc .det code { background: none !important; padding: 0 !important;
  color: var(--ink); font-weight: 600 }

/* 한 문장 쪽 — 여백을 크게 두고 활자로만 말한다 */
.stmt { min-height: 600px; display: flex; flex-direction: column; justify-content: center;
  padding: 0 40px }
.stmtno { font-size: 12px; letter-spacing: .2em; color: var(--brand); font-weight: 700;
  font-variant-numeric: tabular-nums; margin-bottom: 28px }
.stmtq { font-size: 44px; line-height: 1.28; letter-spacing: -.04em; font-weight: 700;
  color: var(--ink); max-width: 20ch }
.stmta { margin-top: 26px; font-size: 19px; line-height: 1.6; letter-spacing: -.022em;
  color: var(--sub); font-weight: 550; max-width: 34ch }
/* .pdfdoc .det .ov 가 gap 을 0 으로 눌러 두었다. 여기가 더 구체적이어야
   숫자 밑 설명이 서로 붙지 않는다 */
.pdfdoc .det.stmt .ov { margin-top: 52px; display: grid !important;
  grid-template-columns: repeat(3, max-content) !important; gap: 0 78px !important }

/* 절 머리 — 제목 왼쪽, 리드 오른쪽. 지면 폭을 다 쓴다 */
.sechd { display: grid; grid-template-columns: .9fr 1.4fr; gap: 0 52px; align-items: start;
  padding-bottom: 18px }
/* 절 번호가 있는 머리만 세 칸. 없는 머리(스킬·자격증)는 그대로 두 칸이다 */
.sechd:has(.secno) { grid-template-columns: 84px .9fr 1.4fr; gap: 0 34px }
/* 절 번호 고스트 — 브랜드 색을 옅게 깔아 기둥으로 쓴다.
   절 시작 쪽은 아래가 비기 쉬운데 이 숫자가 여백을 구도로 만든다 */
.secno { font-size: 62px; font-weight: 700; line-height: .82; letter-spacing: -.06em;
  color: var(--brand, #0066cc); opacity: .17; font-variant-numeric: tabular-nums;
  margin-top: -6px }
.sechd .step { font-size: 10.5px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--brand, var(--muted)); font-weight: 700 }
.sechd .stitle { font-size: 40px; line-height: 1.0; letter-spacing: -.042em; margin-top: 11px }
.sectxt .rline { font-size: 13.6px; font-weight: 650; letter-spacing: -.012em;
  color: var(--brand, var(--ink)); margin-bottom: 8px }
.sectxt .lead { font-size: 13.9px; line-height: 1.62; color: var(--sub); letter-spacing: -.006em }

/* 개요 — 왼쪽 글과 지표, 오른쪽 화면 */
/* 글단을 넓혀야 절이 통째로 한 줄에 들어간다. 좁으면 애써 넣은 줄바꿈
   뒤에서 또 한 번 접혀 두 번 끊긴 것처럼 보인다 */
.ovpage { display: grid; grid-template-columns: 1.32fr 1fr; gap: 38px; align-items: start }
.ovpage .tech { margin-top: 16px }
.ovpage .tech li { font-size: 11.8px; line-height: 1.5; margin-bottom: 4px }
.ovpage .step { font-size: 10.5px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--brand); font-weight: 700 }
.ovpage .stitle { font-size: 34px; line-height: 1.02; letter-spacing: -.045em; margin: 8px 0 12px }
.ovpage .rline { font-size: 14px; font-weight: 650; color: var(--brand); margin-bottom: 10px }
.ovpage .lead { font-size: 12.8px; line-height: 1.68; color: var(--sub); margin-bottom: 14px }
.ovpage .ovshot { justify-self: stretch; align-self: center }
/* 지표 개수가 프로젝트마다 다르다. 3칸 격자에 4개를 넣으면 마지막 하나가
   홀로 다음 줄로 떨어진다. 한 줄로 흘려 개수와 무관하게 서게 한다.
   `.det` 가 `.ovpage` **안**에 있으므로 순서를 뒤집어야 셀렉터가 맞는다 */
.pdfdoc .ovpage .ov { display: flex !important; flex-wrap: nowrap !important;
  gap: 0 26px !important; margin-top: 24px !important;
  grid-template-columns: none !important }
.pdfdoc .ovpage .ov .c { flex: 0 0 auto; white-space: nowrap }
.pdfdoc .ovpage .ov b { font-size: 24px !important; white-space: nowrap }
.pdfdoc .ovpage .ov span { margin-top: 5px; font-size: 11px; white-space: nowrap }
/* 좁은 단에서 목업 둘을 나란히 두면 세로로 접혀 지면을 먹는다.
   개요에는 큰 화면 하나만 싣고 폰만 있는 프로젝트는 그대로 둔다 */
.ovpage .ovshot .browser + .mockimg { display: none }
.ovpage .ovshot .browser { max-width: 100% !important }
/* 폰 화면 하나뿐인 개요는 목업을 키워야 지면이 찬다 */
.ovpage .ovshot .mockimg { max-width: 292px !important; margin: 0 auto }

/* 쪽 단위 격자 — 개수를 정해 두었으니 폭은 균등하게 */
/* 칸 수는 줄에 담긴 개수를 따른다(--cols). 3칸에 2개만 놓으면 오른쪽 한 칸이
   사라진 것처럼 보인다. !important 를 쓰므로 인라인 값이 아니라 변수로 받는다 */
.pgcards, .pgparts { display: grid !important;
  grid-template-columns: repeat(var(--cols, 3), 1fr) !important; gap: 16px }
.pgcards + .pgcards, .pgparts + .pgparts, .pgfeats + .pgfeats { margin-top: 16px }
.pgfeats { display: grid !important;
  grid-template-columns: repeat(var(--cols, 3), 1fr) !important; gap: 12px }
.pgts { display: grid !important; grid-template-columns: 1fr !important; gap: 12px }
/* 한 쪽에 세 건이 들어가도록 조인다. 세 건이 한눈에 보여야 흐름이 읽힌다 */
.pgts .tsitem { padding: 15px 18px }
.pgts .tsitem .t { font-size: 15px; margin-bottom: 10px }
.pgts .tsflow { gap: 10px }
.pgts .tsflow .b { padding: 10px 12px }
.pgts .tsflow p { font-size: 12.2px; line-height: 1.62 }
.pgts .tsflow .lab { font-size: 10px; margin-bottom: 5px }
.pgpress { display: grid !important;
  grid-template-columns: repeat(var(--cols, 2), 1fr) !important; gap: 16px }
/* 표는 한 덩어리로 짠다. 항목마다 아래에 빈 자리를 두지 않는다 */
.pgdtable { display: block !important }
.pdfdoc .det .pgdtable .drow { padding: 12px 0 !important;
  display: grid !important; grid-template-columns: 150px 1fr !important; gap: 28px }
.pdfdoc .det .pgdtable .drow:first-child { border-top: 0 !important; padding-top: 2px !important }
.pdfdoc .det .pgdtable .drow .k { font-size: 11.5px; letter-spacing: .01em;
  text-transform: none; color: var(--muted); font-weight: 650 }
.pdfdoc .det .pgdtable .drow .v { font-size: 14px; line-height: 1.6; letter-spacing: -.008em }
.pgskp { columns: 2; column-gap: 44px }
.pgskp .skp { break-inside: avoid; padding: 9px 0; border-bottom: 1px solid var(--line) }

/* 쪽 안쪽 제목 */
.pgh { font-size: 15px; font-weight: 650; letter-spacing: -.01em; color: var(--sub);
  padding-bottom: 10px; border-bottom: 1px solid var(--line); margin-bottom: 16px }

/* 실제 화면 — 지면을 통째로 쓴다. 포트폴리오에서 화면이 주인공이다.
   자르지 않는다(contain). 잘라서 맞추면 만든 것을 못 보여 준다 */
.fillblk .sechd { flex: none }
.pfgrid { display: flex; gap: 14px; flex: 1 1 auto; min-height: 0;
  align-items: center; justify-content: center }
.pf { margin: 0; border: 0; border-radius: 22px; overflow: hidden; background: #f5f5f7;
  box-sizing: border-box; padding: 22px 22px 0; max-width: 100% }
.pf img { width: 100%; height: auto; border-radius: 8px; display: block }
.pf figcaption { padding: 15px 4px; text-align: center;
  font-size: 12.5px; color: var(--muted); border: 0; letter-spacing: .012em }

/* 더 많은 작업 — 격자 안 미리보기. 여기서도 자르지 않는다 */
.tilepf { margin: 14px 0 0; border: 0; border-radius: 14px; background: #fff;
  overflow: hidden; padding: 0 }
/* 높이를 못 박고 contain 하면 세로로 긴 전체 페이지 캡처 둘레에 흰 여백만
   남는다. 면이 사진을 감싸게 두어 빈 상자가 생기지 않게 한다 */
.tilepf img { max-height: 300px; max-width: 100%; width: auto; height: auto;
  margin: 0 auto; background: #fff; border-radius: 10px; display: block }
.tilepf figcaption { padding: 9px 4px 0; text-align: center; font-size: 11.5px;
  color: var(--muted); border: 0 }
.dochint { font-size: 13px; color: var(--muted); margin-top: 12px }
.dochint a { color: var(--blue); text-decoration: underline; text-underline-offset: 3px }

/* 목업과 도식은 지면 높이를 넘지 않게 묶어 둔다 */
.pdfdoc .device.duo { width: min(620px, 100%) }
.pdfdoc .browser { max-width: 600px }
.pdfdoc .mockimg { max-width: 210px }
.pdfdoc .det .figure img { max-height: 548px; width: auto; max-width: 100%;
  margin: 0 auto; display: block }

/* 쪽 하나를 쓰는 도식. 감싼 면·설명줄까지 합쳐 예산 안에 들어와야 한다.
   넘기면 조판기가 통째로 줄여 도식과 설명 글자가 같이 작아진다.
   위 `.figure img` 와 특정도가 같으므로 반드시 뒤에 와야 이긴다 */
.pdfdoc .det .pgfigure { margin-top: 0 !important }
.pdfdoc .det .pgfigure img { max-height: 536px }
/* 절 머리와 도식이 한 쪽을 같이 쓰는 지면. 도식이 남은 자리를 채운다 */
/* 뒤에 내용이 더 있는 절의 도식 — 한 쪽을 다 먹지 않게 높이를 누른다 */
.figure.figshort img { max-height: 372px; width: auto; margin: 0 auto; display: block }
.figpage { display: flex; flex-direction: column }
.figpage .sechd { flex: none }
.pdfdoc .det.figpage .pgfigure { flex: 1 1 auto; min-height: 0;
  display: flex; flex-direction: column; justify-content: center }
.pdfdoc .det.figpage .pgfigure img { max-height: none; flex: 0 1 auto;
  min-height: 0; object-fit: contain }

/* 더 많은 작업 — 한 줄에 두 장. 사진이 읽히는 최소 크기다.
   사이트에서는 설명 문단이 늘어나 아래를 채운다. 지면에서는 사진 높이가
   짝마다 달라서, 그대로 두면 옆칸끼리 사진 시작 높이가 어긋난다.
   설명은 제 높이로 두고 버튼만 바닥에 붙인다 */
.pairtile { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px }
.pdfdoc .pairtile .tile p { flex: none !important }
.pdfdoc .pairtile .tbtns { margin-top: auto !important; padding-top: 8px }
.pdfdoc .skpx { padding: 11px 0; border-bottom: 1px solid var(--line) }

/* ── 프로필 ───────────────────────────────────────────────────
   이름과 연락처를 왼쪽 기둥에 세우고 이력은 오른쪽 표로 읽힌다.
   서식 문서의 3×3 표가 아니라 사람을 먼저 보여주는 지면이다 */
.pfpage { display: grid; grid-template-columns: .82fr 1.18fr; gap: 64px;
  align-content: center }
.pfid { border-right: 1px solid var(--line); padding-right: 56px }
/* 증명사진. 애플 제품 사진처럼 여백을 넉넉히 두고 모서리만 살짝 둥글린다 */
.pfphoto { width: 132px; aspect-ratio: 3/4; border-radius: 12px; overflow: hidden;
  background: #eef3f8; margin: 0 0 22px }
.pfphoto img { width: 100%; height: 100%; object-fit: cover; display: block }
/* 상자를 이어 실을 때 쓰는 꼬리표 */
.cont { font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing: 0 }
.pfrole { font-size: 12px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--blue); font-weight: 700 }
.pfname { font-size: 68px; line-height: .96; letter-spacing: -.055em; margin: 14px 0 12px }
.pfen { font-size: 13.5px; color: var(--muted); letter-spacing: .01em }
.pfct { margin: 40px 0 0; display: grid; gap: 13px }
.pfct > div { display: grid; grid-template-columns: 52px 1fr; gap: 14px; align-items: baseline }
.pfct dt { font-size: 11px; letter-spacing: .1em; color: var(--muted) }
.pfct dd { margin: 0; font-size: 14px; font-weight: 550; letter-spacing: -.01em; color: var(--ink) }
.pfbody .step { font-size: 10.5px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--muted); font-weight: 700 }
.pfbody .stitle { font-size: 40px; line-height: 1; letter-spacing: -.042em; margin: 11px 0 0 }
.pflead { margin: 20px 0 30px; font-size: 14.2px; line-height: 1.72;
  color: var(--sub); letter-spacing: -.006em }
.pftable { display: grid }
.pfr { display: grid; grid-template-columns: 116px 1fr; gap: 22px; align-items: baseline;
  padding: 15px 0; border-top: 1px solid var(--line) }
.pfr b { font-size: 11.5px; letter-spacing: .06em; color: var(--muted); font-weight: 650 }
.pfr span { font-size: 14.6px; font-weight: 550; letter-spacing: -.014em; line-height: 1.5 }

/* ── 스킬 ─────────────────────────────────────────────────────
   알약 칩을 걷고 활자 굵기로만 주력을 가른다. 분류는 왼쪽 기둥에 세워
   눈이 한 번만 훑으면 되게 한다. 설명은 싣지 않는다 */
.skpage { display: flex; flex-direction: column }
.skmatrix { display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0 }
.smrow { display: grid; grid-template-columns: 158px 1fr; gap: 34px;
  align-content: center; padding: 15px 0; border-top: 1px solid var(--line);
  flex: 1 1 0; min-height: 0 }
.smrow:first-child { border-top: 0 }
.smcat { font-size: 11.5px; letter-spacing: .16em; color: var(--muted); font-weight: 700;
  align-self: center }
.smlist { display: grid; gap: 11px }
.smcore, .smrest { display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline }
.smk { font-size: 21px; font-weight: 700; letter-spacing: -.028em; color: var(--ink) }
.smn { font-size: 14.5px; font-weight: 450; letter-spacing: -.008em; color: var(--muted) }

/* ── 산출물 미리보기 ─────────────────────────────────────────
   읽으라고 넣는 지면이 아니다. 이런 문서를 실제로 썼다는 것만 보이면 된다.
   그래서 글자는 작게 두고 넘치는 줄은 지면에서 잘라 낸다 */
.dpage { display: flex; flex-direction: column }
/* 1fr 은 minmax(auto,1fr) 이라 표가 길면 칸이 늘어나 지면을 뚫는다.
   minmax(0,1fr) 이라야 칸 안에서 잘린다 */
.dpgrid { flex: 1 1 auto; min-height: 0; display: grid;
  grid-template-columns: minmax(0,1fr) minmax(0,1fr);
  grid-template-rows: minmax(0,1fr) minmax(0,1fr); gap: 18px 20px }
.dpcell { min-height: 0; display: flex; flex-direction: column;
  background: #f5f5f7; border-radius: 16px; padding: 14px 14px 0; overflow: hidden }
.dphd { flex: none; display: flex; align-items: baseline; gap: 8px; padding-bottom: 10px }
.dphd b { font-size: 13px; font-weight: 700; letter-spacing: -.018em }
.dphd span { margin-left: auto; font-size: 10.5px; color: var(--muted);
  font-variant-numeric: tabular-nums }
.dpsheet { flex: 1 1 auto; min-height: 0; overflow: hidden;
  background: #fff; border-radius: 8px 8px 0 0; padding: 8px 10px 0 }
.dpsheet table { width: 100%; table-layout: fixed; border-collapse: collapse }
.dpsheet th, .dpsheet td { font-size: 6.2px; line-height: 1.5; text-align: left;
  padding: 2px 4px 2px 0; overflow: hidden; white-space: nowrap;
  text-overflow: ellipsis; letter-spacing: 0 }
.dpsheet th { font-weight: 700; color: var(--sub); border-bottom: .6px solid rgba(0,0,0,.22) }
.dpsheet td { color: var(--muted); border-bottom: .6px solid rgba(0,0,0,.05) }
.dpsheet td.dpg { font-weight: 700; color: var(--sub); background: rgba(0,0,0,.04) }

/* ── 자격증 · 수상 · 교육 ─────────────────────────────────────
   사이트의 접히는 상자를 걷고 괘선으로만 가른다 */
.crpage { display: flex; flex-direction: column }
.crgrid { display: grid; grid-template-columns: 1fr 1.16fr; gap: 54px; margin-top: 4px;
  flex: 1 1 auto; min-height: 0 }
.crcol { display: flex; flex-direction: column }
.crhd { padding-bottom: 13px; border-bottom: 1.5px solid var(--ink) }
.crhd b { display: block; font-size: 17px; font-weight: 700; letter-spacing: -.024em }
.crhd span { display: block; margin-top: 5px; font-size: 12px; color: var(--muted);
  line-height: 1.5 }
.crrow { display: grid; grid-template-columns: 1fr auto; gap: 20px; align-items: baseline;
  padding: 7px 0; border-bottom: 1px solid var(--line) }
.crn b { display: block; font-size: 13.8px; font-weight: 650; letter-spacing: -.016em }
.crn em { display: block; margin-top: 2px; font-style: normal; font-size: 11.4px;
  color: var(--muted); line-height: 1.4 }
.crv { text-align: right; white-space: nowrap }
.crv i { display: block; font-style: normal; font-size: 12px; font-weight: 700;
  color: var(--blue); letter-spacing: -.01em }
.crv span { display: block; margin-top: 3px; font-size: 11.5px; color: var(--muted);
  font-variant-numeric: tabular-nums }
.crnote { margin-top: auto; padding-top: 14px; font-size: 11px; line-height: 1.55;
  color: var(--muted) }
.edugrid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 54px; margin-top: 2px }
.edugrid .crv span { color: var(--ink); font-weight: 650; font-size: 13px }

/* ── 장 표지 아래 가로대 ──────────────────────────────────────
   칩을 흘리면 줄이 들쭉날쭉 접히고, 버튼을 가운데 두면 슬라이드처럼 보인다 */
/* 제목 위쪽에 숨을 두고 기간·기술·링크는 지면 아래에 모아 붙인다.
   가로대와 장 구성 사이가 비면 지면 한가운데에 구멍이 생긴다 */
.chrail { margin-top: auto; padding-top: 22px; border-top: 1px solid var(--line);
  display: grid; gap: 40px; align-items: start }
/* 한글 라벨이라 자간을 벌리지 않는다. 괘선 아래 작은 표제처럼 앉힌다 */
.chcell b { display: block; font-size: 11px; letter-spacing: .01em;
  color: var(--brand); font-weight: 700; margin-bottom: 11px }
.chcell span { font-size: 13.4px; line-height: 1.62; color: var(--sub); letter-spacing: -.008em }
.pdfdoc .det .chlinks .links { display: flex !important; justify-content: flex-start !important;
  gap: 9px; margin: 0 !important; flex-direction: column; align-items: flex-start }
.pdfdoc .det .chlinks .links a { margin: 0 }
.pdfdoc .det .chapwrap .chdesc { max-width: 30ch }
/* 테스트 계정 — 눌러 보려는 사람이 바로 쓰도록 가로대 아래 한 줄로 붙인다 */
.chdemo { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--line);
  display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap }
.chdemo b { font-size: 11px; color: var(--brand); font-weight: 700 }
.chdemo span { font-size: 13.4px; color: var(--ink) }
.chdemo u { text-decoration: none; font-weight: 700;
  font-variant-numeric: tabular-nums }
.chdemo i { font-style: normal; font-size: 12px; color: var(--muted) }
'''.replace('__BODYH__', str(pdfkit.BODY_H))


# ─────────────────────────── 별첨 ───────────────────────────

def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


DOCS_CSS = '''
@page { size: 297mm 210mm; margin: 0 }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact;
  font-family: var(--sans); color: var(--ink); background: #fff; margin: 0 }
.dpage { padding: 34px 46px 30px }
.dsec { break-before: page }
.dpage:first-child .dsec { break-before: auto }
thead { display: table-header-group }
tr { break-inside: avoid }
.dhd { display: flex; align-items: baseline; gap: 12px; margin-bottom: 4px }
.dhd h2 { font-size: 21px; letter-spacing: -.025em }
.dhd .pj { font-size: 10.5px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase;
  color: #fff; background: var(--brand); border-radius: 980px; padding: 4px 11px }
.dsrc { font-size: 11.5px; color: var(--muted); margin-bottom: 11px }
.lgd { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 11px; font-size: 11.5px }
.lgd span { display: inline-flex; align-items: center; gap: 6px; color: var(--sub); font-weight: 600 }
.lgd i { width: 22px; height: 11px; border-radius: 6px; box-shadow: inset 0 0 0 1px rgba(0,0,0,.06) }
table { border-collapse: collapse; width: 100%; font-size: 11px }
th, td { border: 1px solid var(--line); padding: 4px 7px; text-align: left; vertical-align: top;
  white-space: pre-wrap; word-break: keep-all; overflow-wrap: break-word }
th { background: var(--brand); color: #fff; font-weight: 600; white-space: nowrap; letter-spacing: -.01em }
tbody tr:nth-child(even) { background: #fafafc }
td:first-child { white-space: nowrap; font-weight: 600 }
tr.grp td { background: #eef1f6; font-weight: 700 }
td.bar { padding: 3px 4px; min-width: 42px }
td.bar span { display: block; height: 11px; border-radius: 7px; box-shadow: inset 0 0 0 1px rgba(0,0,0,.06) }
td.st { white-space: nowrap; font-weight: 600 }
.dcover { min-height: 640px; display: grid; grid-template-rows: auto 1fr auto; box-sizing: border-box;
  padding: 62px 72px 66px }
.dcover .cvtag { font-size: 11px; letter-spacing: .22em; text-transform: uppercase; color: var(--muted) }
.dcover h1 { font-size: 62px; line-height: 1.04; letter-spacing: -.05em; align-self: center }
.dcover .dlist { border-top: 1px solid var(--line); padding-top: 22px;
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 22px; font-size: 12.5px; color: var(--sub) }
.dcover .dlist b { display: block; font-size: 11px; letter-spacing: .12em; text-transform: uppercase;
  color: var(--muted); margin-bottom: 7px }
'''


def docs_blocks():
    """산출물 문서를 표로 편다.

    행마다 글 길이가 달라 개수를 고정하면 넘치거나 남는다. 그래서 행 높이를
    먼저 재고, 쪽 예산에 맞춰 나눈 뒤 쪽마다 표 머리를 다시 얹는다.
    """
    src = []
    for js, pj, brand in [('docs-cogi.js', 'COGI', '#1c4f8c'),
                          ('docs-tl.js', 'TripLinker', '#a85c28'),
                          ('docs-om.js', '오몽', '#E07B1E')]:
        raw = read('assets/' + js).strip()
        src.append((pj, brand, json.loads(raw[raw.index('=') + 1:].rstrip().rstrip(';'))))

    docs, probe = [], []
    for pj, brand, data in src:
        for key, d in data.items():
            head = ''.join('<th>%s</th>' % esc(h or '·') for h in d['head'])
            rows = []
            for r in d['rows']:
                if isinstance(r, dict) and 'g' in r:
                    rows.append('<tr class="grp"><td colspan="%d">%s</td></tr>'
                                % (len(d['head']), esc(r['g'])))
                    continue
                cells = r.get('c', r) if isinstance(r, dict) else r
                bars = r.get('b') if isinstance(r, dict) else None
                tds = []
                for i in range(len(d['head'])):
                    v = cells[i] if i < len(cells) else ''
                    st = {'완료': 'done', '진행': 'now', '예정': 'todo'}.get(v)
                    if bars and str(i) in bars:
                        tds.append('<td class="bar"><span style="background:%s"></span></td>'
                                   % bars[str(i)])
                    elif st:
                        tds.append('<td class="st %s">%s</td>' % (st, esc(v)))
                    else:
                        tds.append('<td>%s</td>' % esc(v or ''))
                rows.append('<tr>%s</tr>' % ''.join(tds))
            lgd = ''
            if d.get('legend'):
                lgd = '<div class="lgd">%s</div>' % ''.join(
                    '<span><i style="background:%s"></i>%s</span>' % (it['color'], esc(it['who']))
                    for it in d['legend'])
            key_id = '%s-%s' % (pj, key)
            title = ('<div class="dhd"><span class="pj">%s</span><h2>%s</h2></div>'
                     '<div class="dsrc">%s · 시트 「%s」 · %d행</div>%s'
                     % (esc(pj), esc(d['label']), esc(d['file']), esc(d['sheet']),
                        len(d['rows']), lgd))
            docs.append(dict(id=key_id, brand=brand, tag='%s · %s' % (pj, d['label']),
                             head=head, rows=rows, title=title))
            probe.append('<div data-bid="t-%s" style="--brand:%s">%s</div>' % (key_id, brand, title))
            probe.append('<div style="--brand:%s"><table><thead data-bid="h-%s"><tr>%s</tr></thead>'
                         '<tbody>%s</tbody></table></div>'
                         % (brand, key_id, head,
                            ''.join(r.replace('<tr', '<tr data-bid="r-%s-%d"' % (key_id, i), 1)
                                    for i, r in enumerate(docs[-1]['rows']))))

    total = sum(len(d['rows']) for d in docs)
    B = [Block('<div class="dcover"><div class="cvtag">Appendix · 산출물 문서</div>'
               '<h1>산출물 문서<br>17종 · %s행</h1>'
               '<div class="dlist">'
               '<div><b>COGI</b>요구사항 정의서 · 기능 정의서 · WBS · API 명세서 · 테이블 정의서</div>'
               '<div><b>TripLinker</b>요구사항 정의서 · 기능 정의서 · WBS · API 명세서 · '
               '테이블 정의서 · 테스트 케이스</div>'
               '<div><b>오몽</b>요구사항 정의서 · 기능 정의서 · WBS · API 명세서 · '
               '테이블 정의서 · AI 활용 로그</div></div></div>' % format(total, ','),
               newpage=True)]

    for d in docs:
        B.append(Block('<div class="dsec" style="--brand:%s">%s'
                       '<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                       % (d['brand'], d['title'], d['head'], ''.join(d['rows'])),
                       tag=d['tag']))
    return B


def docs_document():
    """부록은 쪽을 직접 짜지 않고 흐름에 맡긴다. 표 머리 반복과 행 보호가 인쇄기 기본 기능이다."""
    B = docs_blocks()
    body = ''.join('<section class="dpage">%s</section>' % b.html for b in B)
    return ('<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">'
            + docs_head() + '</head><body>' + body + '</body></html>')


# ─────────────────────────── 조립 ───────────────────────────

def head_html(extra_css):
    base = style_of(read('index.html'))
    det = scope(style_of(read('projects/cogi.html')), '.det')
    det += scope(style_of(read('projects/omong.html')), '.det')
    return ('<title>정상연 — 백엔드 개발자 포트폴리오</title>'
            '<link rel="stylesheet" href="assets/font/pretendard.css">'
            '<style>%s\n%s\n%s</style>' % (base, det, extra_css))


def docs_head():
    base = style_of(read('index.html'))
    root = re.search(r':root\s*\{(.*?)\}', base, re.S).group(1)
    return ('<title>정상연 — 포트폴리오 산출물</title>'
            '<link rel="stylesheet" href="assets/font/pretendard.css">'
            '<style>:root{%s}%s</style>' % (root, DOCS_CSS))


def compose(blocks, head, foot_title, tmp_measure, tmp_out):
    pdfkit.measure(blocks, head, os.path.join(ROOT, tmp_measure))
    over = [b for b in blocks if b.h > pdfkit.BODY_H]
    if over:
        print('  ! 한 쪽보다 큰 블록 %d개 (최대 %dpx) — 축소해 담는다'
              % (len(over), max(b.h for b in over)))
        for b in over:
            print('      %4dpx  %s  %s' % (b.h, b.tag, re.sub(r'\s+', ' ', b.html)[:96]))
        for b in over:
            b.html = ('<div class="fitpage" style="--fit:%.4f">%s</div>'
                      % (pdfkit.BODY_H / float(b.h) * .985, b.html))
            b.h = pdfkit.BODY_H
    pages = pdfkit.paginate(blocks)
    html = ('<!DOCTYPE html><html lang="ko" class="js"><head><meta charset="UTF-8">'
            + head + '</head><body class="pdfdoc">'
            + pdfkit.render_pages(pages, foot_title) + '</body></html>')
    html = shrink_images(html)
    path = os.path.join(ROOT, tmp_out)
    io.open(path, 'w', encoding='utf-8', newline='').write(html)
    return path, len(pages)


FIT_CSS = ('.fitpage { transform: scale(var(--fit)); transform-origin: top left; '
           'width: calc(100% / var(--fit)) }')


def main():
    os.chdir(ROOT)
    if os.path.isdir(os.path.join(ROOT, IMGDIR)):
        shutil.rmtree(os.path.join(ROOT, IMGDIR))
    print('본편')
    src, n = compose(build_blocks(), head_html(PRINT_CSS + FIT_CSS),
                     '포트폴리오', '_measure.html', '_pdf.html')
    bad = pdfkit.assert_fits(src)
    print('  넘치는 쪽 %s' % (', '.join(bad) if bad else '없음'))
    size, pg = pdfkit.print_pdf(src, os.path.join(OUT, MAIN_PDF), expect=n)
    print('  %s  %.1fMB  %d쪽 (조판 %d쪽)' % (MAIN_PDF, size / 1048576.0, pg, n))

    # 산출물 별첨은 만들지 않는다 (사용자 지시).
    # 만들려면 --docs 를 붙인다
    if '--docs' in sys.argv:
        print('별첨')
        path = os.path.join(ROOT, '_pdf_docs.html')
        io.open(path, 'w', encoding='utf-8', newline='').write(docs_document())
        size, pg = pdfkit.print_pdf(path, os.path.join(OUT, DOCS_PDF))
        print('  %s  %.1fMB  %d쪽' % (DOCS_PDF, size / 1048576.0, pg))


if __name__ == '__main__':
    main()
