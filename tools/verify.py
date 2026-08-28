# -*- coding: utf-8 -*-
"""사이트 정적 검증. redesign2/apple 에서 `python tools/verify.py` 로 실행."""
import io, json, os, re, sys
from urllib.parse import unquote

RESUME_PDF = 'assets/이력서_정상연.pdf'

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ['index.html', 'projects/cogi.html', 'projects/triplinker.html', 'projects/omong.html']
DOCJS = {'cogi': 'docs-cogi.js', 'triplinker': 'docs-tl.js', 'omong': 'docs-om.js'}

# 사용자가 반복해서 금지한 표현 + 코드에 없는 것으로 확인된 문구
BANNED = [
    'A부터', '함께 일할 기회', '연락하기',
    'Redis 블랙리스트', '10분 주기', '10분 배치',
    'Grok', 'Groq → Gemini', 'Claude → GPT → Groq',
]
fails = []


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


def bad(msg):
    fails.append(msg)


for page in PAGES:
    s = read(page)
    name = os.path.basename(page)

    for t in ('section', 'div', 'details', 'summary', 'button', 'ul', 'li', 'a', 'p', 'span'):
        o = len(re.findall(r'<' + t + r'[\s>]', s))
        c = len(re.findall(r'</' + t + r'>', s))
        if o != c:
            bad('%s: <%s> 짝이 안 맞음 (열림 %d / 닫힘 %d)' % (name, t, o, c))

    if 'keep-all' not in s:
        bad('%s: word-break keep-all 없음' % name)
    if re.search(r'\.rv\s*\{\s*opacity:\s*0', s):
        bad('%s: .rv 기본값이 opacity:0 — JS 없으면 콘텐츠가 안 보인다' % name)

    for b in BANNED:
        if b in s:
            bad('%s: 금지 문구 "%s"' % (name, b))

    # 문서 팝업 키가 실제로 등록돼 있는지
    keys = set(re.findall(r'data-doc="([a-z]+)"', s))
    if keys:
        stem = name.replace('.html', '')
        if stem == 'index':
            bad('index.html에 data-doc이 있다 — 문서 팝업은 상세페이지 전용')
        else:
            js = read('assets/' + DOCJS[stem])
            # window.PROJECT_DOCS = { ... }  — JSON으로 파싱해 최상위 키만 본다
            body = js.split('=', 1)[1].strip().rstrip(';')
            have = set(json.loads(body).keys())
            for k in sorted(keys - have):
                bad('%s: data-doc="%s" 가 %s 에 없다 — 클릭해도 무음 실패' % (name, k, DOCJS[stem]))

    # 로컬 자산 존재 확인
    base = os.path.dirname(os.path.join(ROOT, page))
    # <script> 안의 문자열 연결(' + d.shot + ')은 자산 경로가 아니다
    markup = re.sub(r'<script\b.*?</script>', '', s, flags=re.S)
    # data: 는 파일이 아니라 값이다. 파비콘을 이 방식으로 넣어 404 를 없앴다
    for src in re.findall(r'(?:src|href)="((?!https?:|mailto:|tel:|data:|#)[^"]+)"', markup):
        # 한글 파일명은 URL 인코딩해 두었다. 실제 파일을 찾으려면 되돌려야 한다
        rel = unquote(src.split('#')[0].split('?')[0])
        p = os.path.normpath(os.path.join(base, rel))
        if not os.path.exists(p):
            bad('%s: 자산 없음 %s' % (name, src))

# 도식 SVG도 같은 기준으로 본다. 캡션에 "실제 코드 기준"이라고 써 뒀다
for svg in ('assets/cogi-arch.svg', 'assets/triplinker-flow.svg'):
    s = read(svg)
    for b in BANNED + ['@Scheduled', '스냅샷', 'enforceDistanceAndGetOver50']:
        if b in s:
            bad('%s: 코드에 없는 표현 "%s"' % (os.path.basename(svg), b))

idx = read('index.html')

hours = [int(x) for x in re.findall(r'class="hr">(\d+)h<', idx)]
if sum(hours) != 1024:
    bad('교육 시수 합계가 %d — 1024여야 한다' % sum(hours))

awards = idx.count('class="pz"')
if awards != 13:
    bad('자격증·수상 행이 %d개 — 자격증 5 + 수상 8 = 13이어야 한다' % awards)

chips = set(re.findall(r'<button class="sk[^"]*" data-sk="([a-z0-9]+)"', idx))
panels = set(re.findall(r'class="skp[^"]*" id="sk-([a-z0-9]+)"', idx))
for k in sorted(chips - panels):
    bad('스킬 칩 "%s" 에 대응하는 패널이 없다' % k)
for k in sorted(panels - chips):
    bad('스킬 패널 "%s" 에 대응하는 칩이 없다' % k)

for need in ('id="about"', 'id="skills"', 'id="credits"', 'id="work"', 'id="more"', 'id="archiving"'):
    if need not in idx:
        bad('index.html에 %s 섹션이 없다' % need)

# 자격증·수상은 프로젝트 뒤로 뺐다 (AI-ENGINEER-PLAN). AI 직무에서는 프로젝트가 먼저 보여야 한다
SECTIONS = ('about', 'skills', 'work', 'more', 'credits', 'archiving')
order = [idx.index('id="%s"' % s) for s in SECTIONS]
if order != sorted(order):
    bad('섹션 순서가 프로필 → 주요 스킬 → 프로젝트 → 추가 작업 → 자격증·수상 → 링크 가 아니다')

if RESUME_PDF not in unquote(idx):
    bad('네비바에 이력서 PDF 링크가 없다')

if fails:
    print('FAIL %d건' % len(fails))
    for f in fails:
        print('  - ' + f)
    sys.exit(1)
print('OK — %d개 페이지 통과' % len(PAGES))
