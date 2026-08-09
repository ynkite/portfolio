# 인수인계 — 포트폴리오 사이트 · 제출용 PDF

새 세션에서 이 파일만 읽으면 이어서 작업할 수 있다.
작업 폴더는 `C:\Users\USER\Downloads\ynkite.github.io\redesign2\apple` 이다.

참고 경로
- 이전 대화 원본 `C:\Users\USER\.claude\projects\C--Users-USER-Downloads-ynkite-github-io\54371171-d5bb-4fcc-893a-d096871737db.jsonl`
- 최초 요구사항 `C:\Users\USER\Downloads\ynkite.github.io\TODO.md` (멘토링 피드백 2026-07-30 포함)
- 승인된 계획 `C:\Users\USER\.claude\plans\vivid-yawning-yao.md`
- 이력서 원문 `C:\Users\USER\Downloads\이력서_수정본_정상연.txt`

---

## 1. 절대 규칙

- **커밋에 `Co-Authored-By: Claude` 를 넣지 않는다.** PR 본문의 `Generated with Claude Code` 표기도 넣지 않는다
- **커밋된 API 키는 언급하지 않는다.** 사용자가 직접 처리한다 (원문: "커밋된 api는 내가 알아서 할게 언급하지마")
- 수치·고유명사를 지어내지 않는다. **코드에 없는 것은 쓰지 않는다**
- 줄바꿈은 `.` 또는 `,` 뒤에서만. 문장 중간에서 끊지 않는다
- 카드 안쪽은 명사 종결, 카드 밖은 존댓말. 마케팅체·과장·슬로건 금지
- 콘텐츠가 안 보이는 사고 금지 — JS가 죽어도 `.rv`와 스킬 패널은 보여야 한다
- 되돌릴 수 있게 작업한다. 백업은 `tools/_backup/2026-07-31/`, `tools/_backup/2026-08-03-pre-apple/`

## 2. 사용하는 스킬

사용자가 매번 지정한 스킬이다. **`/apple-design` 을 주 언어로 삼는다.**

| 스킬 | 쓰는 곳 |
|---|---|
| `apple-design` | **메인.** §15 크기별 자간·행간, §16 단순성·장인정신·길찾기 |
| `design-taste-frontend-v1` | 안티슬롭. 가운데 정렬 히어로 금지, 3열 카드 나열 금지, 이모지 금지 |
| `high-end-visual-design` | 여백 확대, 중첩 구조, 일반 1px 회색 테두리·강한 그림자 금지 |
| `minimalist-ui` | 편집 지면 톤, 괘선 그룹핑, 순백 대신 오프블랙 |
| `humanize-korean` / `ai-tell-detector` | 새로 쓴 한국어는 반드시 탐지기에 건다 |
| `ponytail` | 도구 코드는 최단 경로로. 불필요한 추상화 금지 |
| `full-output-enforcement` | 생략 표시(`// ...`) 금지, 항상 완결된 코드 |

윤문 결과 반영 이력: S1 0건, S2 6건 중 5건 반영. "스킬별 설명 → 기술별 설명" 지적은 사이트 섹션명이 "스킬"이라 **의도적으로 미반영**.

### 스킬 설치 위치 — 계정을 바꿔도 그대로 쓸 수 있다

스킬은 이 문서가 아니라 디스크에 있다. 확인 완료.

| 위치 | 스킬 | 계정 변경 시 |
|---|---|---|
| `<프로젝트>/.claude/skills/` | **apple-design**, emil-design-eng, animation-vocabulary, prototype 등 8개 | 폴더와 함께 이동하므로 그대로 |
| `~/.claude/skills/` (윈도우 사용자 프로필) | design-taste-frontend-v1, high-end-visual-design, minimalist-ui, humanize-korean, ai-tell-detector, ponytail, full-output-enforcement, caveman 계열 등 30여 개 | 윈도우 계정이 같으면 그대로 |

즉 **같은 PC · 같은 윈도우 계정이면 클로드 계정만 바꿔도 전부 쓸 수 있다.**
마켓플레이스 플러그인 스킬만 계정에 묶일 수 있는데, 이 작업에 필요한 것은 전부 위 두 곳에 있다.

## 3. 지금 상태

| | |
|---|---|
| 사이트 | `index.html` + `projects/{cogi,triplinker,omong}.html`. 라이브 `https://ynkite.github.io/portfolio/` |
| 본편 PDF | `assets/포트폴리오_정상연.pdf` — 최신 **68쪽**. 디스크 파일은 잠김 때문에 56쪽 판일 수 있음 |
| 별첨 PDF | `assets/포트폴리오_정상연_산출물.pdf` — 49쪽, 산출물 문서 17종 1,526행 |
| 이력서 | `assets/이력서_정상연_포트폴리오사이트용.pdf` 하나뿐. 네비에서 퍼센트 인코딩으로 링크 |
| git | `ynkite/portfolio` · 브랜치 `feat/portfolio-pdf` · **PR #5 열려 있음** (#3 #4 머지됨) |

```bash
python tools/build_pdf.py     # PDF 두 개 생성
python tools/verify.py        # OK — 4개 페이지 통과
python tools/manifest.py      # 올릴 파일 목록
python tools/sync_repo.py <저장소경로>
```

## 4. 파일 지도

```
HANDOVER.md      이 파일
index.html       메인. 8개 스냅 페이지
projects/        상세 3종
assets/
  image/         갤러리 사진 78장 (가공 완료)
  font/          Pretendard 로컬 사본 — PDF 조판 결정성에 필수
  docs-*.js      산출물 문서 데이터 (JSON으로 파싱 가능)
  docviewer.js   문서 팝업
  프로젝트 사진/  원본 캡처 (git 제외, 81MB)
tools/
  build_pdf.py   조립·CSS·표지·목차·장 표지. 실행 진입점
  pdfdoc.py      사이트에서 '내용'을 자료로 뽑는다 (마크업이 아니라 구조)
  pdfkit.py      높이 실측 → 쪽에 담기 → 인쇄. 넘침 검사·잠김 감지
  pdfpages.py    절 머리·격자·화면 사진을 지면 단위로 짠다
  verify.py      정적 검사
  manifest.py    참조되는 자산만 골라 목록화
  sync_repo.py   그 목록대로 저장소에 옮긴다
  shots.py composite_shots.py stagepass_shots.py
  triplinker_shots.py phone_norm.py split_panels.py   캡처 가공
```

## 5. PDF 설계 결정과 이유

- **A4 가로(297×210mm)**, 인쇄 레이아웃 폭 **1123px**. 사이트는 860px 아래로 내려가야 열이 접히므로 데스크톱과 구조가 같다
- **`zoom` 으로 1280px 를 축척하는 방법은 못 쓴다.** Chrome 인쇄는 `zoom` 을 무시한다(적용·미적용 페이지 수 동일). 실측으로 확인함
- **글꼴은 로컬 Pretendard 고정.** CDN 을 쓰면 측정 렌더와 인쇄 렌더에서 적용 여부가 달라 높이가 어긋나 **잘린다**
- **쪽당 개수를 고정하지 않는다.** 글 길이 편차 때문에 넘치거나 남는다. 격자는 한 줄씩 내고 몇 줄이 들어갈지는 실측 높이로 정한다
- **안전분 18px**(`pdfkit.SAFETY`), 넘침 검사는 조판 예산이 아니라 실제 여백 높이(`pdfkit.LIMIT`) 기준
- 상세페이지 CSS 는 메인과 34개 셀렉터가 겹쳐 `.det` 아래로 가둔 뒤 합친다
- 사진은 표시 크기의 두 배인 1100px 로 축소. `-erd` `-arch` `-flow` 만 원본 해상도 유지
- **본편은 실측 조판, 별첨은 흐름 조판.** 별첨은 표가 전부라 `thead` 반복과 `tr { break-inside: avoid }` 가 정답이다

### PDF 내용 규칙 (사용자 지정)

- 메인 프로젝트는 **흐름 순서로 6장씩**, 서브는 **대표 화면 1장씩**
- **영상은 넣지 않는다**
- 1페이지에 `https://ynkite.github.io/portfolio/` 를 눌러서 갈 수 있게
- **내용을 모두 유지한다.** 사이트를 못 보는 사람이 이것만 받아도 빠지는 게 없어야 한다
- 산출물 문서는 분량이 커서 별첨으로 분리하고 본편에서 링크로 잇는다
- 스킬은 알약 칩 없이 활자 굵기로 주력을 가르고, 설명은 **주력 10개만**

## 6. 밟은 함정 (재발 방지)

1. **PDF 파일 잠김** — 뷰어가 열고 있으면 크롬이 조용히 실패한다. 파일이 안 바뀌는데 "완료"로 보고한 사고가 있었다. **결과 파일의 수정 시각과 쪽수를 반드시 확인할 것**
2. **CDN 글꼴 비결정성** — 5절 참고
3. **`<details name="credits">`** — 배타 아코디언이라 `open` 을 붙여도 하나만 열린다. `name` 속성을 지워야 한다
4. **`.phone` 클래스 충돌** — 사이트에 폰 목업 `.phone` 이 있다. PDF 전용 클래스는 `pf` 접두어를 쓴다
5. **별첨 빌드가 본편 사진 폴더를 삭제** — `shrink_images` 에서 `rmtree` 를 없앴다
6. **`.pdfdoc section { padding: 0 }` 이 `.page` 여백까지 지움** — `.page section` 으로 좁혔다
7. **좁은 단에서 목업 둘이 세로로 접혀** 638px 를 먹었다. 개요에는 큰 화면 하나만 싣는다
8. **`animation-fill-mode: both`** 는 시작 전 `opacity:0` 을 미리 적용해 콘텐츠를 영구히 감춘다. `forwards` 를 쓴다
9. **`overflow-x: hidden` 을 `body` 에 주면** body 가 스크롤 컨테이너가 되어 `html` 스냅이 죽는다
10. 헤드리스 검증 시 `--user-data-dir` 는 랜덤, 출력은 절대경로

## 7. 사이트 쪽 결정 (되돌리지 말 것)

- **8개 스냅 페이지** + 우측 스텝 인디케이터. `html { scroll-snap-type: y mandatory }`, `.snap { min-height: calc(100vh - 48px) }`
- 상세페이지에서 뒤로 오면 떠났던 스냅 페이지로 복귀. `sessionStorage` + `getBoundingClientRect` 기반 8회 자기교정 루프. `behavior:'instant'` 필수
- 프로필 표 2행은 `스킬 | 자격증 · 수상 | 대표 프로젝트` 한 줄
- 스킬 4열 Backend · AI · DB·Infra · Frontend·Etc. 패널 높이 고정(126px)
- 자격증 · 수상 · 교육 3개 `<details>`, 교육 합계 정확히 **1024h**, 경진대회 **8회**
- 상세 3종에 `04 · DEPLOY & TEST` 섹션 존재
- 버튼 색: 상세보기 = 프로젝트 브랜드색, 사이트 바로가기 = 검정
- 저장소는 **루트가 곧 사이트**다. 중복이던 `apple/` 폴더는 PR #3 에서 삭제했다

## 8. 이미 고친 사실 관계 (되돌리면 안 됨)

코드를 다시 읽고 바로잡은 것이다. 면접에서 코드를 열면 바로 드러난다.

| 고친 것 | 근거 |
|---|---|
| TripLinker `Redis 블랙리스트` **삭제** | Redis 의존성 없음. `refresh_tokens` 테이블에 저장하고 로그아웃 시 하드 삭제 |
| TripLinker `10분 주기 배치 캐싱` **삭제** | `@Scheduled` 0건, 스냅샷 테이블 없음. 요청 시점 조회 |
| AI 역할 분담 정정 | Claude 가 1차 생성, Groq 는 실패 시 폴백 |
| 40/50km 극성 정정 | AI 가 넣은 장소는 삭제, 사용자가 직접 요청한 장소는 유지하고 알림에 담음 |
| 오몽 모델 체인 정정 | 3단(`claude-sonnet-4-6, gpt-5.2, gemini-3-flash-preview`). Groq 는 주석에만 |
| 오몽 Ollama | 라이브 경로는 MindLogic 게이트웨이. Ollama 는 로컬 대체 경로 |
| Laravel 경진대회 금상 | **PetVillage** 로 받았다. DEVICE SHOP 은 수상 없는 프로젝트 |

`verify.py` 가 금지 문구로 막고 있다 — `Redis 블랙리스트`, `10분 주기`, `10분 배치`, `Groq → Gemini`, `Grok`, `A부터`, `함께 일할 기회`, `연락하기`

## 9. 사용자가 확정한 사실

- PetVillage 는 **라라벨 프로젝트**. 스택 `PHP · Laravel · MariaDB`
- DEVICE SHOP 개발 기간 **2025.04–05**, 수상 없음
- 교육 대우능력개발원 KDT 총 **1024h**, 경진대회 수상 **8회**, 자격증 5건
- 서브 프로젝트 메타는 `기간 · 개인` 형식으로 통일 (`약 N개월` 표기 제거)
- 사이트가 쓰는 이력서는 `assets/이력서_정상연_포트폴리오사이트용.pdf` 하나뿐

## 10. 이미지 파이프라인

- **오몽 폰 목업 11장** — 그림자를 걷어 내면 전부 `428×882`. 확대 없이 원본 그대로, 라운드 30px 로 알파 처리
- **합성 캡처**(WindyCamp · DEVICE SHOP · PetVillage) — 흰 여백 구조를 실측해 화면별로 되쪼갬. 좌표는 `composite_shots.py` 에 박혀 있다
- **StagePass** — 원본이 브라우저 크롬 없는 전체 페이지 캡처라 자르지 않는다. 모달 2장만 어두운 막을 벗기고 라운드 처리
- **TripLinker** — 2560×1528 전체 창 캡처. 위 181px(탭·주소창·북마크)과 오른쪽 8px(스크롤바)만 잘라낸다
- 갤러리 총 78장 — COGI 11 · TripLinker 20 · 오몽 11 · StagePass 10 · WindyCamp 6 · DEVICE SHOP 6 · PetVillage 11 · Triplan 2 · Analyze Festa 1

## 11. 남은 일 (우선순위)

1. **포트폴리오 구성을 다시 짠다** ← 최우선

   **지금 무엇이 문제인가.** 사용자 표현 그대로 "그냥 나열만 하고 잘리고 전체적으로 이상하다".
   - 내용을 쪽에 흘려 담는 방식이라 **문서 목차처럼 읽힌다.** 개요·분석·설계·개발·배포·담당·트러블슈팅·기능 순서는 문서 구성이지 포트폴리오 구성이 아니다
   - 쪽마다 밀도가 비슷해 **강약이 없다.** 어디가 중요한지 안 보인다
   - 잘리거나 어중간하게 비는 쪽이 남는다

   **참고 자료** `C:\Users\USER\OneDrive\Desktop\3학년 A반 정상연_포트폴리오(V2).pptx`
   (25장 · 이미지 49개). 이 파일의 **구성 방식**을 참고한다. 판형을 따라하라는 뜻이 아니다.
   - **간지를 따로 둔다** — 제목만 있는 쪽으로 장을 나눈다 (3쪽 "프로필", 8쪽 "프로젝트 목록")
   - **한 쪽에 한 주제** — 핵심 기능을 3장으로 쪼갰지 한 장에 몰아넣지 않았다
   - **주력만 깊게** — TripLinker 10장, 서브 프로젝트는 각 1장
   - 쪽마다 역할이 다르다 — 표지 · 목차 · 간지 · 개요 · 화면 · 기술 · DB · 성장 포인트

   **판형은 결정 사항이지 목표가 아니다.** 지금은 A4 가로다.
   16:9 슬라이드로 바꿀지, A4 세로로 갈지, 지금 판형을 유지할지 먼저 정하고 들어간다.
   또 다른 참고 `C:\Users\USER\OneDrive\Desktop\2024001910정상연_이력서.pdf` (A4 세로 10쪽)

   이미 넣어 둔 것 — 장 표지, 한 문장 쪽(문제·해결을 44px 활자로), 전면 대표 화면.
   방향은 맞으나 그 뒤가 여전히 나열이다. 거기서부터 손본다.
2. 잠긴 `assets/포트폴리오_정상연.pdf` 를 최신본으로 갱신
3. PR #5 검토 후 머지
4. TripLinker 소개 영상 (아직 `준비 중` 자리표시자)
5. 루트 `index.html`(시안 목록) 교체 — 이력서에 `https://ynkite.github.io` 가 적혀 있다
6. DEVICE SHOP · Triplan · Analyze Festa repo URL 3건이 `github.com/ynkite` 기본값
7. 목업 좌우 화살표
8. COGI 테스트 케이스 문서 — 사용자가 작성 중. 오면 `docs-cogi.js` 에 `test` 키 추가 후 버튼 한 줄

## 12. 환경과 준비

확인 완료된 상태다.

| | |
|---|---|
| Python | PIL(Pillow) **12.2.0** 설치됨. numpy 는 쓰지 않는다 |
| Chrome | `C:\Program Files\Google\Chrome\Application\chrome.exe` — `pdfkit.CHROME` 에 하드코딩 |
| gh CLI | `ynkite` 로 로그인됨. 클로드 계정과 무관하다 |
| 글꼴 | `assets/font/PretendardVariable.woff2` (2MB). 없으면 PDF 조판이 어긋난다 |

**저장소 작업 사본은 임시 폴더에 있었고 세션이 끝나면 사라진다.** 다시 만들려면:

```bash
git clone https://github.com/ynkite/portfolio.git <작업경로>
cd <작업경로> && git checkout feat/portfolio-pdf
# 그 다음 사이트 폴더에서
python tools/sync_repo.py <작업경로>
```

집 디렉터리(`C:\Users\USER`)가 커밋 없는 git 저장소로 잡혀 있다.
**거기서는 절대 커밋하지 않는다.** 홈 디렉터리 전체가 올라간다.

저장소 루트의 `.gitignore` 에는 원본 캡처 모음·백업·PDF 빌드 부산물이 들어 있다.

## 13. 검증 습관

- 고친 뒤에는 반드시 `python tools/verify.py`
- PDF 는 빌드 로그의 `넘치는 쪽` 이 **없음**인지 확인하고, 결과 파일의 **수정 시각과 쪽수**를 직접 읽어 확인
- 헤드리스 렌더로 눈으로 본다. 프리뷰 창은 `file://` 자산을 캐시해 갱신이 안 된다
- 새로 쓴 한국어는 `ai-tell-detector` 에 건다
