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

MAIN_PDF = '포트폴리오_정상연.pdf'
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
      <div class="cvrole">Backend Developer</div>
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
      키오스크 앞에서 말로 주문을 돕는 서비스를 만들었습니다.<br>세 프로젝트 모두 AWS 배포까지 마쳤고 두 곳에서 팀장을 맡았습니다.</p>
    <dl class="cvmeta">
      <div><dt>웹</dt><dd><a href="{site}">ynkite.github.io/portfolio</a></dd></div>
      <div><dt>메일</dt><dd>j.sangyeon6@gmail.com</dd></div>
      <div><dt>전화</dt><dd>010-4211-3521</dd></div>
      <div><dt>깃허브</dt><dd>github.com/ynkite</dd></div>
    </dl>
  </div>
</div>'''

TOC_ROWS = [
    ('프로필', '이름 · 학력 · 스킬 · 경력 · 연락처'),
    ('스킬', 'Backend · AI · DB · Frontend, 칩별 설명 21건'),
    ('자격증 · 수상 · 교육', '자격증 5 · 경진대회 8 · KDT 1024h'),
    ('01 COGI', 'AI 코드리뷰 학습 플랫폼 — 개요 · 실제 화면 6장 · 상세'),
    ('02 TripLinker', 'AI 여행 플래너 — 개요 · 실제 화면 6장 · 상세'),
    ('03 오몽', '키오스크 도우미 — 개요 · 실제 화면 6장 · 상세'),
    ('04 더 많은 작업', 'StagePass · WindyCamp · DEVICE SHOP · PetVillage · Triplan · Analyze Festa'),
    ('링크 · 연락처', ''),
]


def toc_html():
    rows = ''.join(
        '<li><b>%s</b><span>%s</span></li>' % (t, d) for t, d in TOC_ROWS)
    return '''<div class="tocwrap">
  <div class="tochd"><span class="kick">Contents</span><h2>목차</h2></div>
  <div class="tocgrid">
    <ol class="toclist">%s</ol>
    <aside class="tocside">
      <div class="tsblk"><b>3</b><span>팀 프로젝트<br>전부 AWS 배포</span></div>
      <div class="tsblk"><b>2</b><span>팀장을 맡은<br>프로젝트</span></div>
      <div class="tsblk"><b>1024h</b><span>대우능력개발원<br>KDT 이수</span></div>
      <div class="tsblk"><b>8회</b><span>교내외<br>경진대회 수상</span></div>
      <p class="tsnote">산출물 문서는 17종 1,526행입니다.
        요구사항 정의서, 기능 정의서, WBS, API 명세서, 테이블 정의서, 테스트 케이스, AI 활용 로그.
        분량이 커서 별첨 <a href="%s">「포트폴리오_정상연_산출물.pdf」</a>로 나눴습니다.</p>
    </aside>
  </div>
</div>''' % (rows, DOCS_URL)


CH_TOC = '개요 · 실제 화면 · 분석 · 설계 · 개발 · 배포와 테스트 · 담당 파트 · 트러블슈팅 · 주요 기능'


def chapter_html(no, name, brand, kick, desc, meta, chips, links, toc=CH_TOC):
    return ('<div class="det chapwrap" style="--brand:%s"><div class="chap">'
            '<div class="chno">%s</div>'
            '<div class="chbody"><div class="chkick">%s</div><h2>%s</h2>'
            '<div class="chdesc">%s</div><div class="chmeta">%s</div>'
            '%s%s</div></div>'
            '<div class="chtoc"><b>이 장의 구성</b><span>%s</span></div></div>'
            % (brand, no, kick, name, desc, meta, chips, links, toc))


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


def wrap_det(html, brand):
    return '<div class="det" style="--brand:%s"><div class="wrap">%s</div></div>' % (brand, html)


def build_blocks():
    """지면용 쪽들을 짠다. 쪽마다 담을 개수를 정해 두어 어중간하게 비지 않는다."""
    ix = pdfdoc.index_parts()
    B = []

    B.append(Block(COVER.replace('{site}', SITE), newpage=True))
    B.append(Block(toc_html(), newpage=True, tag='목차'))

    # ── 프로필 : 왼쪽 표, 오른쪽 소개
    B.append(Block(
        '<div class="sechd"><div><div class="step">PROFILE</div><h2 class="stitle">프로필</h2></div>'
        '<div class="sectxt"><p class="lead">%s</p></div></div>' % ix['lead'],
        newpage=True, keepnext=True, tag='프로필'))
    B.append(Block(ix['abgrid'], tag='프로필', head=('PROFILE', '프로필')))

    # ── 스킬 : 칩을 걷고 글자 굵기로 주력을 가른다. 설명은 주력만
    cats, desc = pdfdoc.skills()
    rows = ''
    for c in cats:
        names = ''.join(
            '<span class="%s">%s</span>' % ('smk' if k else 'smn', n) for _, n, k in c['items'])
        rows += '<div class="smrow"><div class="smcat">%s</div><div class="smlist">%s</div></div>' % (
            c['name'], names)
    B.append(Block(
        '<div class="sechd"><div><div class="step">SKILLS</div><h2 class="stitle">스킬</h2></div>'
        '<div class="sectxt"><p class="lead">굵게 쓴 것이 주력입니다. 설명은 주력 열 개만 실었습니다.'
        '<br>나머지는 실무에서 쓸 수 있는 수준으로 익혔습니다.</p></div></div>',
        newpage=True, keepnext=True, tag='스킬'))
    B.append(Block('<div class="skmatrix">%s</div>' % rows, tag='스킬', head=('SKILLS', '스킬')))

    core = [(sid, desc[sid]) for c in cats for sid, _, k in c['items'] if k and sid in desc]
    B.append(Block('<h3 class="pgh">주력 스킬</h3>', keepnext=True, tag='스킬', head=('SKILLS','주력 스킬')))
    for pair in pdfpages.chunk(core, 2):
        cells = ''.join(
            '<div class="skd"><b>%s</b><i>%s</i><p>%s</p></div>' % (d['name'], d['level'], d['text'])
            for _, d in pair)
        B.append(Block('<div class="skdrow">%s</div>' % cells, tag='스킬', head=('SKILLS', '주력 스킬')))

    # ── 자격증 · 수상 · 교육
    B.append(Block(
        '<div class="sechd"><div><div class="step">CREDITS</div>'
        '<h2 class="stitle">자격증 · 수상 · 교육</h2></div>'
        '<div class="sectxt"><p class="lead">자격증 5건을 취득했고, 교내외 경진대회에서 8회 수상했습니다.'
        '<br>대우능력개발원 KDT는 1024시간을 이수했습니다.</p></div></div>',
        newpage=True, keepnext=True, tag='자격증 · 수상'))
    for f in ix['folds']:
        f = f.replace('<details class="fold"', '<details open class="fold"')
        f = re.sub(r'\sname="credits"', '', f)   # 배타 아코디언이면 하나만 열린다
        B.append(Block(f, tag='자격증 · 수상', head=('CREDITS', '자격증 · 수상 · 교육')))

    # ── 프로젝트 세 장
    for ch in CHAPTERS:
        pj = pdfdoc.project(ch['file'])
        brand, tag = ch['brand'], ch['name']
        B.append(Block(chapter_html(ch['no'], pj['name'], brand, pj['kick'], pj['desc'],
                                    pj['meta'], pj['chips'], pj['links']),
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
            % (ov['rline'], ov['lead'], det_only(ovhtml, brand), feat['bullets'],
               feat['device']),
            newpage=True, tag=tag))

        # 한 문장 쪽 — 문제와 해결을 크게, 지표는 그 아래
        q, a = STATEMENT[ch['sec']]
        B.append(Block(
            '<div class="det stmt" style="--brand:%s"><div class="stmtno">%s</div>'
            '<p class="stmtq">%s</p><p class="stmta">%s</p>%s</div>'
            % (brand, ch['no'], q, a, ovhtml),
            newpage=True, tag=tag))

        kind, shots = SHOTS[ch['sec']]
        # 대표 화면 한 장을 크게 — 포트폴리오에서 화면이 주인공이다
        f0, c0 = shots[0]
        B.append(Block(
            '<div class="det hero1" style="--brand:%s"><img src="assets/image/%s" alt="%s">'
            '<div class="cap">%s</div></div>' % (brand, f0, c0, c0),
            newpage=True, tag=tag))
        B += pdfpages.shot_pages(kind, shots[1:], brand, tag)

        for sec in pj['sections'][1:]:
            B += pdfpages.section_pages(sec, brand, tag)

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
    B.append(Block(ix['archcards'], tag='링크', head=('LINK', '링크 · 연락처')))

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
@page { size: 297mm 210mm; margin: 0 }
html, body { background: #fff; margin: 0 }
body { -webkit-print-color-adjust: exact; print-color-adjust: exact }

.page { position: relative; width: 296.9mm; height: 209.6mm; overflow: hidden;
  box-sizing: border-box; padding: 82px 64px 60px; background: #fff;
  break-after: page; break-inside: avoid }
.page:last-child { break-after: auto }
.page.bleed { padding: 0 }
.pgbody { display: flex; flex-direction: column }
.pgbody > * { flex: none }

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
.toclist li { counter-increment: t; padding: 10px 0; border-bottom: 1px solid var(--line) }
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
.chapwrap { min-height: 634px; display: flex; flex-direction: column; justify-content: center }
.chap { display: grid; grid-template-columns: 168px 1fr; gap: 8px; align-items: start }
.chtoc { margin-top: auto; padding-top: 18px; border-top: 1px solid var(--line);
  display: flex; gap: 16px; align-items: baseline; font-size: 12.5px; color: var(--muted) }
.chtoc b { font-size: 10.5px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--brand); font-weight: 700; flex: none }
.chno { font-size: 104px; font-weight: 700; line-height: .8; letter-spacing: -.06em;
  color: var(--brand); opacity: .16; font-variant-numeric: tabular-nums }
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
  padding: 22px 24px !important; box-shadow: none !important }
.pdfdoc .det .cards, .pdfdoc .det .parts { gap: 16px !important; padding: 0 !important }
.pdfdoc .det .card .n, .pdfdoc .det .part .no {
  display: block; font-size: 10.5px; letter-spacing: .16em; text-transform: uppercase;
  color: var(--brand); font-weight: 700; background: none !important; padding: 0 !important;
  margin-bottom: 9px }
.pdfdoc .det .card h4, .pdfdoc .det .part h4 {
  font-size: 17px; font-weight: 700; letter-spacing: -.024em; margin-bottom: 9px }
.pdfdoc .det .card p, .pdfdoc .det .part li {
  font-size: 13.4px; line-height: 1.66; color: var(--sub); letter-spacing: -.004em }
.pdfdoc .det .part ul { margin: 0; padding-left: 16px }

/* 표 — 상자를 없애고 넓은 줄 간격으로 읽게 한다 */
.pdfdoc .det .dtable { background: none !important; border: 0 !important;
  border-radius: 0 !important; padding: 0 !important; overflow: visible !important }
.pdfdoc .det .drow { background: none !important; border: 0 !important;
  border-top: 1px solid rgba(0,0,0,.08) !important; border-radius: 0 !important;
  padding: 16px 0 !important; box-shadow: none !important }
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

.pf { border: 0 !important; border-radius: 22px !important;
  background: #f5f5f7 !important; padding: 20px 20px 0 !important; overflow: hidden }
.pf img { border-radius: 10px 10px 0 0; display: block }
.pf figcaption { border: 0 !important; padding: 14px 4px !important; text-align: center;
  font-size: 12px; color: var(--muted); background: none !important }

/* 한 문장 쪽 — 여백을 크게 두고 활자로만 말한다 */
.stmt { min-height: 600px; display: flex; flex-direction: column; justify-content: center;
  padding: 0 40px }
.stmtno { font-size: 12px; letter-spacing: .2em; color: var(--brand); font-weight: 700;
  font-variant-numeric: tabular-nums; margin-bottom: 28px }
.stmtq { font-size: 44px; line-height: 1.28; letter-spacing: -.04em; font-weight: 700;
  color: var(--ink); max-width: 20ch }
.stmta { margin-top: 26px; font-size: 19px; line-height: 1.6; letter-spacing: -.022em;
  color: var(--sub); font-weight: 550; max-width: 34ch }
.stmt .ov { margin-top: 52px; display: grid !important;
  grid-template-columns: repeat(3, max-content) !important; gap: 0 72px !important }

/* 대표 화면 — 거의 전면으로 */
.hero1 { background: #f5f5f7; border-radius: 24px; padding: 30px 30px 0;
  box-sizing: border-box }
.hero1 img { width: 100%; max-height: 520px; object-fit: contain; border-radius: 10px; display: block }
.hero1 .cap { padding: 18px 0 26px; text-align: center; font-size: 12.5px; color: var(--muted) }

/* 절 머리 — 제목 왼쪽, 리드 오른쪽. 지면 폭을 다 쓴다 */
.sechd { display: grid; grid-template-columns: .9fr 1.4fr; gap: 52px; align-items: start;
  padding-bottom: 26px }
.sechd .step { font-size: 10.5px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--brand, var(--muted)); font-weight: 700 }
.sechd .stitle { font-size: 46px; line-height: 1.0; letter-spacing: -.045em; margin-top: 12px }
.sectxt .rline { font-size: 14px; font-weight: 650; letter-spacing: -.012em;
  color: var(--brand, var(--ink)); margin-bottom: 9px }
.sectxt .lead { font-size: 14.6px; line-height: 1.72; color: var(--sub); letter-spacing: -.006em }

/* 개요 — 왼쪽 글과 지표, 오른쪽 화면 */
.ovpage { display: grid; grid-template-columns: 1.02fr 1fr; gap: 44px; align-items: start }
.ovpage .tech { margin-top: 16px }
.ovpage .tech li { font-size: 11.8px; line-height: 1.5; margin-bottom: 4px }
.ovpage .step { font-size: 10.5px; letter-spacing: .2em; text-transform: uppercase;
  color: var(--brand); font-weight: 700 }
.ovpage .stitle { font-size: 34px; line-height: 1.02; letter-spacing: -.045em; margin: 8px 0 12px }
.ovpage .rline { font-size: 14px; font-weight: 650; color: var(--brand); margin-bottom: 10px }
.ovpage .lead { font-size: 12.8px; line-height: 1.68; color: var(--sub); margin-bottom: 14px }
.ovpage .ovshot { justify-self: stretch; align-self: center }
/* 좁은 단에서 목업 둘을 나란히 두면 세로로 접혀 지면을 먹는다.
   개요에는 큰 화면 하나만 싣고 폰만 있는 프로젝트는 그대로 둔다 */
.ovpage .ovshot .browser + .mockimg { display: none }
.ovpage .ovshot .browser { max-width: 100% !important }
.ovpage .ovshot .mockimg { max-width: 210px !important; margin: 0 auto }

/* 쪽 단위 격자 — 개수를 정해 두었으니 폭은 균등하게 */
.pgcards, .pgparts { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 16px }
.pgcards + .pgcards, .pgparts + .pgparts, .pgfeats + .pgfeats { margin-top: 16px }
.pgfeats { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 12px }
.pgts { display: grid !important; grid-template-columns: 1fr !important; gap: 12px }
/* 한 쪽에 세 건이 들어가도록 조인다. 세 건이 한눈에 보여야 흐름이 읽힌다 */
.pgts .tsitem { padding: 15px 18px }
.pgts .tsitem .t { font-size: 15px; margin-bottom: 10px }
.pgts .tsflow { gap: 10px }
.pgts .tsflow .b { padding: 10px 12px }
.pgts .tsflow p { font-size: 12.2px; line-height: 1.62 }
.pgts .tsflow .lab { font-size: 10px; margin-bottom: 5px }
.pgpress { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 16px }
.pgdtable { display: block !important }
.pgskp { columns: 2; column-gap: 44px }
.pgskp .skp { break-inside: avoid; padding: 9px 0; border-bottom: 1px solid var(--line) }
.pgfigure img { max-height: 590px; width: auto; max-width: 100%; margin: 0 auto; display: block }

/* 쪽 안쪽 제목 */
.pgh { font-size: 15px; font-weight: 650; letter-spacing: -.01em; color: var(--sub);
  padding-bottom: 10px; border-bottom: 1px solid var(--line); margin-bottom: 16px }

/* 실제 화면 */
.pfgrid { display: grid; gap: 12px; align-items: start }
.pfgrid.pfwide { grid-template-columns: 1fr 1fr }
.pfgrid.pfphone { grid-template-columns: repeat(3, 1fr) }
.pf { margin: 0; border: 1px solid var(--line); border-radius: 12px; overflow: hidden; background: #fff }
.pf img { width: 100%; display: block }
.pfgrid.pfphone .pf img { background: #f7f7f9 }
.pf figcaption { padding: 7px 10px; font-size: 11px; color: var(--sub);
  border-top: 1px solid var(--line); letter-spacing: .01em }
.tilepf { margin: 14px 0 0 }
.tilepf img { aspect-ratio: 16 / 10; object-fit: cover; object-position: top center }
.dochint { font-size: 13px; color: var(--muted); margin-top: 12px }
.dochint a { color: var(--blue); text-decoration: underline; text-underline-offset: 3px }

/* 목업과 도식은 지면 높이를 넘지 않게 묶어 둔다 */
.pdfdoc .device.duo { width: min(620px, 100%) }
.pdfdoc .browser { max-width: 600px }
.pdfdoc .mockimg { max-width: 210px }
.pdfdoc .det .figure img { max-height: 520px; width: auto; max-width: 100%;
  margin: 0 auto; display: block }
.pfgrid.pfwide .pf img { aspect-ratio: 16 / 9; object-fit: cover; object-position: top center }
.pfgrid.pfphone { grid-template-columns: repeat(3, 1fr) }
.pfgrid.pfphone .pf img { height: 566px; object-fit: contain; background: #f7f7f9 }

/* 더 많은 작업 — 한 줄에 두 장. 사진이 읽히는 최소 크기다 */
.pairtile { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 18px }
.pairtile .tilepf img { aspect-ratio: 16 / 10 }
.pdfdoc .skpx { padding: 11px 0; border-bottom: 1px solid var(--line) }
'''


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
                     '정상연 · 포트폴리오', '_measure.html', '_pdf.html')
    bad = pdfkit.assert_fits(src)
    print('  넘치는 쪽 %s' % (', '.join(bad) if bad else '없음'))
    size, pg = pdfkit.print_pdf(src, os.path.join(OUT, MAIN_PDF))
    print('  %s  %.1fMB  %d쪽 (조판 %d쪽)' % (MAIN_PDF, size / 1048576.0, pg, n))

    print('별첨')
    path = os.path.join(ROOT, '_pdf_docs.html')
    io.open(path, 'w', encoding='utf-8', newline='').write(docs_document())
    size, pg = pdfkit.print_pdf(path, os.path.join(OUT, DOCS_PDF))
    print('  %s  %.1fMB  %d쪽' % (DOCS_PDF, size / 1048576.0, pg))


if __name__ == '__main__':
    main()
