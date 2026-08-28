# -*- coding: utf-8 -*-
"""요약 포트폴리오 지면 디자인 — 사이트 언어를 그대로 지면으로 옮긴다.

사이트에서 가져온 것
  · 색      --ink #1d1d1f · --sub #6e6e73 · --muted #86868b · --line #d2d2d7
            --gray #f5f5f7 · --blue #0066cc
  · 칩      .sk 는 회색 알약, .sk.core 는 검은 알약. 사이트에서 가장 눈에 띄는 요소다
  · 카드    .tile 은 테두리가 없다. 회색으로 채우고 모서리를 24px 로 크게 깎는다
  · 배경    .feat.gray 처럼 절마다 회색과 흰색을 번갈아 쓴다
  · 제목    .hero h1 은 아주 크고 자간이 -.055em 이다
  · 버튼    .pbtn 은 border-radius 980px 알약

앞선 판이 진부했던 이유
  테두리 있는 흰 상자와 얇은 회색 선만 반복했다. 사이트는 정반대로
  선을 거의 쓰지 않고 면과 활자 크기로 나눈다. 그 규칙을 따른다.
"""

CSS = """
:root { --ink:#1d1d1f; --sub:#6e6e73; --muted:#86868b; --line:#d2d2d7;
  --gray:#f5f5f7; --blue:#0066cc; --brand:#0066cc }
* { box-sizing:border-box }
html, body { overflow:hidden; background:#fff; margin:0;
  -webkit-print-color-adjust:exact; print-color-adjust:exact }
@page { size:297mm 210mm; margin:0 }
body { font-family:'Pretendard Variable', Pretendard, -apple-system, sans-serif;
  color:var(--ink); font-size:13px; line-height:1.6; letter-spacing:-.01em;
  overflow-wrap:break-word }
/* 낱말 안에서 끊지 않는 것은 표시용 문장에만 건다.
   전체에 걸면 표의 열 폭 계산이 흔들려 칸 안이 토막 난다 */
.chdesc, .cvlead, .shlead, .bfdesc, .chname, .cvname, .sheet h2 { word-break:keep-all }

.page { position:relative; width:296.9mm; height:209.6mm; overflow:hidden;
  padding:56px 60px 52px; background:#fff; break-after:page; break-inside:avoid }
.page:last-child { break-after:auto }
.page.gray { background:var(--gray) }
.pgbody { height:__BODYH__px; display:flex; flex-direction:column }
.pgbody > * { flex:1 1 auto; min-height:0 }

.pfoot { position:absolute; left:60px; right:60px; bottom:20px; display:flex; gap:14px;
  align-items:baseline; font-size:9.5px; letter-spacing:.1em; color:var(--muted) }
.pfoot b { color:var(--brand); font-weight:700; letter-spacing:.06em }
.pfoot span:last-child { margin-left:auto; font-variant-numeric:tabular-nums }

h1,h2,h3 { margin:0; font-weight:700 }
h1 { letter-spacing:-.055em; line-height:.92 }
h2 { letter-spacing:-.048em; line-height:1.0 }
h3 { letter-spacing:-.022em; line-height:1.2 }
p { margin:0 }


/* 판 머리 — 선을 긋지 않는다. 크기 차이로만 나눈다 */
.sheet { display:flex; flex-direction:column; height:100% }
.shd { margin-bottom:24px }
.kick { font-size:10px; letter-spacing:.24em; text-transform:uppercase;
  color:var(--brand); font-weight:700 }
.shd h2 { font-size:40px; margin-top:9px }
.shlead { margin-top:12px; font-size:13.5px; color:var(--sub); line-height:1.66; max-width:640px }
.mt2 { margin:22px 0 10px; font-size:10.5px; color:var(--muted);
  letter-spacing:.14em; text-transform:uppercase; font-weight:600 }


/* 쪽 머리 오른쪽에 붙는 바깥 링크 */
.shd { position:relative }
.shlink { position:absolute; right:0; bottom:6px; text-decoration:none;
  display:inline-flex; align-items:center; gap:8px;
  font-size:13px; font-weight:700; letter-spacing:-.022em;
  color:#fff; background:var(--brand); border-radius:980px; padding:9px 18px 10px }

/* ───────── 1쪽 표지 ─────────
   상자를 두르지 않는다. 굵은 선 하나로 단을 끊고, 나머지는 실선과 여백으로 나눈다.
   2쪽 연표의 축과 같은 두께(1.5px)를 여기서도 쓴다. */
.cv { display:grid; grid-template-columns:206px 1fr; gap:0 54px; height:100% }
.cvL, .cvR { display:flex; flex-direction:column; min-height:0 }
.cvphoto { width:206px; aspect-ratio:3/4; overflow:hidden; background:#eef3f8;
  border-radius:3px }
.cvphoto img { width:100%; height:100%; object-fit:cover; display:block }
.cvct { margin:18px 0 0; padding-top:12px; border-top:1.5px solid var(--ink);
  display:grid; gap:0 }
.cvct > div { display:grid; grid-template-columns:52px 1fr; gap:10px;
  align-items:baseline; padding:7px 0; border-bottom:1px solid var(--line) }
.cvct > div:last-child { border-bottom:0 }
.cvct dt { font-size:9px; letter-spacing:.1em; color:var(--muted); white-space:nowrap }
.cvct dd { margin:0; font-size:11.4px; font-weight:600; color:var(--ink);
  letter-spacing:-.02em; word-break:break-all }

.cvrole { font-size:10.5px; letter-spacing:.2em; text-transform:uppercase;
  font-weight:700; color:var(--blue) }
.cvname { font-size:79px; margin:6px 0 3px; letter-spacing:-.055em }
.cven { font-size:12.6px; color:var(--muted); letter-spacing:0 }
.cvlead { margin:20px 0 0; padding-top:17px; border-top:1.5px solid var(--ink);
  font-size:14px; line-height:1.72; color:var(--sub); letter-spacing:-.022em }
.cvlead b { color:var(--ink); font-weight:600 }

/* 수치 — 상자 대신 세로 실선으로 칸을 가른다 */
.cvnums { margin-top:20px; padding:16px 0 17px; border-top:1px solid var(--line);
  border-bottom:1px solid var(--line); display:grid; grid-template-columns:repeat(3,1fr) }
.cvnums > div { padding-left:24px; border-left:1px solid var(--line) }
.cvnums > div:first-child { padding-left:0; border-left:0 }
.cvnums b { display:block; font-size:38px; font-weight:700; letter-spacing:-.055em;
  line-height:1; font-variant-numeric:tabular-nums }
.cvnums span { display:block; margin-top:8px; font-size:10.4px; line-height:1.48;
  color:var(--muted) }

/* 이력 — 이름표와 값을 두 칸으로 벌린다 */
.cvrows { margin-top:4px }
.cvrow { display:grid; grid-template-columns:66px 1fr; gap:14px; align-items:baseline;
  padding:7px 0; border-bottom:1px solid var(--line) }
.cvrow b { font-size:10px; font-weight:700; letter-spacing:.02em; color:var(--blue);
  white-space:nowrap }
.cvrow span { font-size:12px; letter-spacing:-.02em; color:var(--ink) }

/* 차례 — 상자 없이 번호 · 이름 · 설명 · 쪽수의 네 칸 */
.cvidx { list-style:none; margin:auto 0 0; padding:15px 0 0;
  border-top:1.5px solid var(--ink) }
.cvidx li { display:grid; grid-template-columns:30px 1fr auto; gap:14px;
  align-items:baseline; padding:8px 0; border-bottom:1px solid var(--line) }
.cvidx li:last-child { border-bottom:0; padding-bottom:0 }
.cvidx b { font-size:11px; font-weight:700; letter-spacing:.06em; color:var(--muted);
  font-variant-numeric:tabular-nums }
.cvidx span { font-size:19px; font-weight:700; letter-spacing:-.035em }
.cvidx span i { font-style:normal; margin-left:12px; font-size:11.6px; font-weight:400;
  color:var(--muted); letter-spacing:-.01em }
.cvidx em { font-style:normal; font-size:10.4px; font-weight:700; letter-spacing:.06em;
  color:var(--brand); font-variant-numeric:tabular-nums }


/* 사이트 주소 — 표지에서 가장 크게 잡는 한 덩이. 눌러서 바로 열린다 */
.cvsite { margin-top:auto; display:block; text-decoration:none; color:#fff;
  background:var(--blue); border-radius:18px; padding:19px 18px 17px }
.cvsk { display:block; font-size:9px; letter-spacing:.16em; text-transform:uppercase;
  font-weight:700; opacity:.72 }
.cvsu { display:block; margin-top:8px; font-size:15.4px; font-weight:700;
  letter-spacing:-.032em; line-height:1.25; word-break:break-all }
.cvsn { display:block; margin-top:10px; padding-top:9px;
  border-top:1px solid rgba(255,255,255,.28);
  font-size:9.6px; letter-spacing:-.01em; opacity:.86 }
.cvsn i { font-style:normal; float:right; font-size:11px; font-weight:700; opacity:1 }

/* ───────── 2쪽 연표 ─────────
   축 하나가 왼쪽에서 오른쪽으로 흐른다. 위에는 낱개 사건이 층을 달리해 매달리고,
   아래에는 기간이 있는 것이 막대로 깔린다. 같은 달에 셋이 몰려도 서로 비킨다. */
.tl { position:relative; margin:6px 0 4px }

.tlmarks { position:relative; height:calc(16px + var(--tiers) * 52px) }
.tlev { position:absolute; bottom:0; width:0;
  display:flex; flex-direction:column; align-items:flex-start }
.tlev::after { content:''; position:absolute; bottom:-5px; left:-4px;
  width:9px; height:9px; border-radius:50%; background:#fff;
  border:2px solid var(--ink); box-sizing:border-box }
.tlev.award::after { background:var(--ink) }
.tlev i { width:1px; background:var(--line); flex:0 0 auto }
.tlcard { width:150px; box-sizing:border-box; padding:0 0 7px }
.tlcard u { display:block; text-decoration:none; font-size:9.4px; letter-spacing:.06em;
  color:var(--muted); font-variant-numeric:tabular-nums; margin-bottom:2px }
.tlcard b { display:block; font-size:11px; font-weight:650; letter-spacing:-.024em;
  line-height:1.28 }
.tlcard em { display:block; margin-top:3px; font-style:normal; font-size:9.8px;
  font-weight:700; color:var(--muted) }
.tlev.award .tlcard em { color:var(--blue) }

/* 축 — 굵은 가로선 하나. 눈금은 아래로 짧게 떨군다 */
.tlaxis { position:relative; height:26px; border-top:1.5px solid var(--ink) }
.tk { position:absolute; top:0; width:0 }
.tk::before { content:''; position:absolute; top:0; left:0; width:1px; height:4px;
  background:var(--line) }
.tk span { position:absolute; top:7px; left:0; transform:translateX(-50%);
  font-size:9px; letter-spacing:.06em; color:var(--muted); white-space:nowrap }
.tk.big::before { height:8px; width:1.5px; background:var(--ink) }
.tk.big span { top:10px; transform:translateX(-2px); font-size:15px; font-weight:700;
  letter-spacing:-.03em; color:var(--ink); font-variant-numeric:tabular-nums }

/* 기간 — 축 아래로 막대 세 개 */
.tlbars { margin-top:18px; display:grid; gap:9px }
.tlrow { position:relative; height:35px }
.tlbar { position:absolute; top:0; height:21px; box-sizing:border-box;
  background:var(--ink); border-radius:11px; color:#fff;
  display:flex; align-items:center; gap:8px; padding:0 12px; overflow:hidden }
.tlbar b { font-size:10.4px; font-weight:650; letter-spacing:-.02em; white-space:nowrap }
.tlbar em { font-style:normal; font-size:9.4px; font-weight:600; opacity:.62;
  white-space:nowrap }
.tlbar.open { border-radius:11px 3px 3px 11px;
  background:linear-gradient(90deg, var(--ink) 0 82%, rgba(29,29,31,.28)) }
.tlsub { position:absolute; top:23px; font-size:9.6px; color:var(--muted);
  white-space:nowrap; letter-spacing:-.01em }

/* 스킬 — 칩 대신 활자 굵기로 나눈다 */
.skwrap { margin-top:auto; padding-top:8px }
/* 갈래마다 한 줄. 이름표를 왼쪽에 세우고 오른쪽으로 쭉 편다 */
.skgrid { border-top:1.5px solid var(--ink) }
.skrow { display:grid; grid-template-columns:86px 1fr; gap:16px; align-items:baseline;
  padding:6.5px 0; border-bottom:1px solid var(--line) }
.skrow:last-child { border-bottom:0 }
.skrow h4 { margin:0; font-size:9.6px; font-weight:700; color:var(--blue);
  letter-spacing:.05em; white-space:nowrap }
.skrow p { margin:0; font-size:10.8px; line-height:1.5; letter-spacing:-.018em }
.skrow b { font-weight:700 }
.skrow span { color:var(--muted) }


/* 내용이 적어 지면이 남는 쪽 — 줄 간격을 벌려 아래를 비우지 않는다 */
.sheet.airy .etabs { gap:30px }
.sheet.airy .evt th { padding-bottom:13px }
.sheet.airy .evt td { padding:22px 12px 22px 0 }
.sheet.airy .fgrid { margin-top:18px }
.sheet.airy .frow { padding:19px 2px 19px 0 }
.sheet.airy .mt2 { margin:30px 0 10px }
.sheet.airy .shlead { margin-top:16px }

/* ───────── 프로젝트 표지 ───────── */
.chap { display:flex; flex-direction:column; height:100% }
.chtop { display:flex; align-items:flex-start; gap:26px }
.chno { font-size:120px; font-weight:700; line-height:.72; letter-spacing:-.07em;
  color:var(--brand); opacity:.15; font-variant-numeric:tabular-nums; margin-top:-6px }
.chkick { font-size:10.5px; letter-spacing:.22em; text-transform:uppercase;
  color:var(--brand); font-weight:700 }
.chtop h1 { font-size:66px; margin:9px 0 14px }
.chdesc { font-size:18px; font-weight:600; color:var(--sub); line-height:1.46;
  letter-spacing:-.024em; max-width:680px }
/* 수치 — 1쪽과 같은 규칙. 상자를 두르지 않고 세로 실선으로 가른다 */
.chstats { margin-top:22px; padding:17px 0 18px; border-top:1.5px solid var(--ink);
  border-bottom:1px solid var(--line);
  display:grid; grid-auto-flow:column; grid-auto-columns:1fr }
.chstats > div { padding-left:26px; border-left:1px solid var(--line) }
.chstats > div:first-child { padding-left:0; border-left:0 }
.chstats b { display:block; font-size:36px; font-weight:700; line-height:1;
  letter-spacing:-.055em; color:var(--brand); font-variant-numeric:tabular-nums }
.chstats span { display:block; margin-top:8px; font-size:10.6px; color:var(--muted);
  line-height:1.5 }
.chbody { margin-top:22px; display:grid; grid-template-columns:1.3fr 1fr; gap:40px; flex:1;
  min-height:0 }
.chbody h3 { font-size:10.5px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); margin-bottom:11px; font-weight:600 }
.chbody .lead { font-size:13.4px; line-height:1.74; color:var(--sub) }
.chbody .lead b { color:var(--ink); font-weight:600 }
/* 주요 기능 — 번호를 흐리게 앞세우고 실선으로 칸을 끊는다. 두 단으로 흐른다 */
.fgrid { margin-top:14px; display:grid; grid-template-columns:1fr 1fr;
  gap:0 40px; border-top:1px solid var(--line) }
.frow { display:grid; grid-template-columns:26px 1fr; gap:0 12px;
  align-items:baseline; padding:11px 2px 11px 0; border-bottom:1px solid var(--line) }
.frow > u { grid-row:span 2; text-decoration:none; font-size:10px; font-weight:700;
  letter-spacing:.04em; color:var(--brand); opacity:.45;
  font-variant-numeric:tabular-nums }
.frow > b { font-size:12.4px; font-weight:700; letter-spacing:-.024em }
.frow > span { font-size:11px; line-height:1.55; color:var(--muted);
  letter-spacing:-.012em; margin-top:3px }
.frow > span b { color:var(--ink); font-weight:600 }
.mrow { display:grid; grid-template-columns:94px 1fr; gap:12px; padding:7px 0;
  font-size:11.6px; line-height:1.55 }
.mrow + .mrow { border-top:1px solid var(--line) }
.mrow b { font-size:10px; letter-spacing:.03em; text-transform:uppercase;
  color:var(--muted); font-weight:600; padding-top:2px; white-space:nowrap }
.mrow span { color:var(--sub); word-break:break-word }

/* ───────── 실제 화면 ───────── */
.scgrid { flex:1; display:grid; grid-template-columns:repeat(3,1fr);
  grid-template-rows:1fr 1fr; gap:16px; min-height:0 }
/* 세로로 긴 화면은 한 줄에 넉 장. 같은 지면에서 두 배 넘게 커진다.
   칸 높이를 그림에 맞춰 위아래 빈 곳을 없앤다 */
.scgrid.tallshots { grid-template-columns:repeat(4,1fr); grid-template-rows:auto;
  gap:20px; align-content:center }
.scgrid.tallshots .scimg { flex:0 0 auto }
.scgrid.tallshots .scimg img { width:100%; height:auto; max-height:none }
.sc { margin:0; display:flex; flex-direction:column; min-height:0;
  background:#fff; border:1px solid var(--line); border-radius:10px;
  padding:10px 10px 8px }
.scimg { flex:1; min-height:0; border-radius:8px; overflow:hidden;
  display:flex; align-items:center; justify-content:center }
.scimg img { max-width:100%; max-height:100%; object-fit:contain; display:block }
.sc figcaption { margin-top:9px; font-size:10.4px; color:var(--muted); text-align:center }

/* ───────── 설계 · 담당 ───────── */
/* 설계 — 상자를 빼고 실선 위에 여섯 칸을 얹는다. 본문의 굵은 글씨는 줄 안에 그대로 둔다 */
.dgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px 34px }
.dcard { border-top:1px solid var(--line); padding-top:11px }
.dn { font-size:9.4px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--brand); font-weight:700 }
.dcard > b { display:block; margin:6px 0 6px; font-size:13.2px; letter-spacing:-.026em;
  line-height:1.3 }
.dcard p { font-size:10.8px; line-height:1.56; color:var(--sub); letter-spacing:-.012em }
.dcard p b { display:inline; font-size:inherit; margin:0; color:var(--ink);
  font-weight:600 }
.dcard p code { font-size:9.8px }

/* 담당 파트 — 주요 기능과 같은 규칙 */
.plist { display:grid; grid-template-columns:1fr 1fr; gap:0 34px;
  border-top:1px solid var(--line) }
.prow { display:grid; grid-template-columns:1fr; gap:0; padding:9px 0;
  border-bottom:1px solid var(--line) }
.prow b { font-size:11.6px; font-weight:700; letter-spacing:-.022em }
.prow span { display:block; margin-top:3px; font-size:10.6px; color:var(--muted);
  line-height:1.5; letter-spacing:-.012em }

/* ───────── 개발과 평가 ───────── */
.egraph { border-top:1px solid var(--line); border-bottom:1px solid var(--line);
  padding:10px 0 2px; margin-bottom:13px }
/* viewBox 가 680×300 이라 폭이 아니라 높이에 걸린다. 그래서 지면에서는 70% 로 줄어든다.
   줄어든 만큼 안쪽 활자와 선을 키워야 읽힌다 */
.egraph svg { width:100%; height:auto; max-height:214px; display:block; margin:0 auto }
.sheet.tight .egraph svg { max-height:146px }
.etabs { flex:1; display:grid; gap:14px; align-content:start; min-height:0 }
.evt { width:100%; border-collapse:collapse; font-size:11.4px }
.evt th { text-align:left; font-size:9.4px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--muted); font-weight:600; padding:0 12px 6px 0 }
.evt td { padding:5.5px 12px 5.5px 0; border-top:1px solid var(--line);
  vertical-align:top; line-height:1.46 }
.evt td.nm { font-weight:600; letter-spacing:-.014em }
.evt td.ch { color:var(--muted); font-size:10.8px }
.evt tr.dim td { color:var(--muted) }
.evt b { color:var(--ink) }
.evt code { font-size:10.2px; color:var(--sub) }
.dipmark { color:#c2410c; font-weight:700; margin-right:3px }

/* ───────── 문제 해결 ───────── */
.tgrid { display:grid; grid-template-columns:1fr 1fr; gap:13px }
.tcard { border-top:1.5px solid var(--ink); padding:12px 0 0 }
.tcard > b { display:block; font-size:13.2px; letter-spacing:-.022em; margin-bottom:9px }
.trow { display:grid; grid-template-columns:32px 1fr; gap:10px; padding:3px 0; font-size:11px }
.trow em { font-style:normal; font-size:9.4px; letter-spacing:.07em; color:var(--brand);
  font-weight:700; padding-top:2px }
.trow span { color:var(--sub); line-height:1.56 }
.trow code, .dep code { font-size:10.2px; color:var(--sub) }
.dep { display:grid; grid-template-columns:1fr 1fr; gap:0 22px }

/* ───────── 더 많은 작업 ───────── */
.mgrid { flex:1; display:grid; grid-template-columns:repeat(3,1fr);
  grid-template-rows:1fr 1fr; gap:14px; min-height:0 }
.mcard { border-top:1px solid var(--line); padding:11px 0 0;
  display:flex; flex-direction:column; min-height:0 }
.mimg { flex:1; min-height:0; border-radius:9px; overflow:hidden; background:var(--gray);
  margin-bottom:10px; display:flex; align-items:center; justify-content:center }
.mimg img { max-width:100%; max-height:100%; object-fit:contain; display:block }
.mcard b { font-size:13px; letter-spacing:-.022em }
.mm { font-size:10px; color:var(--brand); font-weight:700; margin-top:2px }
.mcard p { margin-top:5px; font-size:10.6px; line-height:1.5; color:var(--muted) }

/* ───────── 링크 ───────── */
/* 마지막 쪽 — 주소 하나가 지면의 주인공이다 */
.bigsite { margin-top:auto }

.bigsite { margin-top:30px; display:block; text-decoration:none; color:#fff;
  background:var(--blue); border-radius:16px; padding:22px 26px 20px }
.bsk { display:block; font-size:9.4px; letter-spacing:.2em; text-transform:uppercase;
  font-weight:700; opacity:.72 }
.bsu { display:block; margin-top:7px; font-size:27px; font-weight:700;
  letter-spacing:-.042em; line-height:1.1 }
.bsn { display:block; margin-top:12px; padding-top:10px;
  border-top:1px solid rgba(255,255,255,.3); font-size:10.6px; opacity:.88 }
.bsn i { font-style:normal; float:right; font-size:12px; font-weight:700; opacity:1 }

.lgrid { margin-top:30px; display:grid; grid-template-columns:repeat(4,1fr);
  gap:0 30px; border-top:1px solid var(--line) }
.lrow { display:block; text-decoration:none; color:inherit; padding:15px 0 2px }
.lrow b { display:block; font-size:9.4px; letter-spacing:.13em; text-transform:uppercase;
  color:var(--muted); font-weight:700 }
.lrow span { display:block; margin-top:8px; font-size:14.4px; font-weight:700;
  letter-spacing:-.032em; word-break:break-all }
.lrow em { display:block; margin-top:6px; font-style:normal; font-size:10.4px;
  color:var(--muted); line-height:1.5 }


/* ───────── 링크 표시 ─────────
   종이에서도 「여기 누르면 열린다」 가 보여야 한다.
   글 속의 주소만 파란 글씨 + 밑줄 + 화살표로 묶는다.
   색을 이미 깔아 둔 덩이(파란 판·버튼)는 건드리지 않는다. */
.chmeta .addr a, .trow a, .dep a, .mrow a, a.lrow span {
  color:var(--blue); text-decoration:underline; text-underline-offset:2.5px;
  text-decoration-thickness:1px; text-decoration-color:rgba(0,102,204,.42) }
.chmeta .addr a::after, .trow a::after, .dep a::after, .mrow a::after {
  content:'↗'; font-size:.82em; margin-left:3px; font-weight:700;
  text-decoration:none; display:inline-block }
a.lrow span::after { content:'↗'; font-size:.72em; margin-left:5px;
  display:inline-block; text-decoration:none }
/* 링크가 아닌 줄(전화)은 밑줄도 파란색도 쓰지 않는다 */
.lrow { color:inherit; text-decoration:none }
/* ───────── 꺾은선 그래프 ───────── */
.trend { width:100%; height:auto; display:block; overflow:visible }
.trend .grid { stroke:var(--line); stroke-width:1.6 }
.trend .ln { fill:none; stroke-width:3.4; stroke-linejoin:round; stroke-linecap:round }
.trend .ln.ceil { stroke:var(--line); stroke-width:2.2; stroke-dasharray:8 7 }
.trend .ln.hit { stroke:var(--brand); stroke-width:3.8 }
.trend .ax { font-size:15px; fill:var(--muted) }
.trend .ax.ar { text-anchor:end }
.trend .ax.am { text-anchor:middle }
.trend .ax.sm { font-size:13.5px }
.trend .val { font-size:16px; font-weight:600; text-anchor:middle }
.trend .val.last { font-size:18.5px; font-weight:700 }
.trend .lg { font-size:15.5px; font-weight:600 }
.trend .lg.dim2 { fill:var(--muted); font-weight:500 }
.trend .lg.hitlg { fill:var(--brand) }
.trend .lg.dip2 { fill:#c2410c; font-size:14px; font-weight:600 }
.trend .dot.hitdot { fill:var(--brand) }
.trend .dip { fill:#fff; stroke:#c2410c; stroke-width:2.4 }

/* ═══════════ 편집 체계 ═══════════
   1) 프로젝트 표지는 브랜드 색 전면. 사이트의 --pb 를 지면 전체로 넓힌 것이다
   2) 내용 쪽에는 왼쪽에 세로 레일을 세운다. 어느 프로젝트인지 늘 붙어 다닌다
   3) 본문은 레일 오른쪽으로 밀어 비대칭 판을 만든다
   4) 선은 표 안에서만 쓴다. 나머지는 면과 활자 크기로 나눈다 */

.page.brandfill { background:var(--brand); color:#fff; padding:64px 68px 56px }
.page.brandfill .pfoot { color:rgba(255,255,255,.62) }
.page.brandfill .pfoot b { color:#fff }

/* 세로 레일 — 쪽마다 왼쪽에 붙는 얇은 기둥 */
.rail { position:absolute; left:34px; top:56px; bottom:52px; width:16px;
  display:flex; flex-direction:column; align-items:center; justify-content:space-between }
.rail .rl { writing-mode:vertical-rl; text-orientation:mixed; font-size:9px;
  letter-spacing:.28em; text-transform:uppercase; color:var(--brand); font-weight:700;
  white-space:nowrap }
.rail .rn { font-size:10px; font-weight:700; color:var(--brand);
  font-variant-numeric:tabular-nums; opacity:.5 }
.rail i { flex:1; width:1px; background:var(--brand); opacity:.18; margin:10px 0 }
.page.hasrail { padding-left:84px }

/* ───────── 장 표지 ─────────
   색을 지면에 붓지 않는다. 왼쪽 가장자리에 브랜드 색 띠 하나를 세우고,
   판면은 본문 쪽과 같은 흰 바탕 · 실선으로 간다. 장이 바뀐 것은 띠와 번호로 안다. */
.page.chapter { padding-left:112px }
.page.chapter::before { content:''; position:absolute; left:0; top:0; bottom:0;
  width:30px; background:var(--brand) }
.page.chapter::after { content:''; position:absolute; left:30px; top:0; bottom:0;
  width:1px; background:var(--line) }
/* 이름이 표의 td.ch 와 겹치면 칸이 세로로 쪼개진다. 반드시 chpg 로 둔다 */
.chpg { display:flex; flex-direction:column; height:100% }

/* 머리 — 번호와 갈래 이름을 실선 하나로 잇는다 */
.chhd { display:flex; align-items:center; gap:16px; margin-bottom:26px }
.chhd em { font-style:normal; font-size:15px; font-weight:700; letter-spacing:-.02em;
  color:var(--brand); font-variant-numeric:tabular-nums }
.chhd i { flex:0 0 56px; height:1.5px; background:var(--brand) }
.chhd span { font-size:10.5px; letter-spacing:.22em; text-transform:uppercase;
  font-weight:700; color:var(--muted) }

.chname { font-size:104px; letter-spacing:-.058em; line-height:.94; margin:0 }
.chdesc { margin:22px 0 0; font-size:17px; font-weight:500; line-height:1.62;
  letter-spacing:-.026em; color:var(--sub); max-width:800px }
.chdesc b { color:var(--ink); font-weight:600 }

.chmeta { margin-top:auto; padding-top:24px; border-top:1.5px solid var(--ink) }
.chmeta .cvrow { grid-template-columns:80px 1fr }
.chmeta .cvrow b { color:var(--brand) }
.chmeta .addr span { font-size:11.4px }
.chmeta .addr a { color:var(--blue); text-decoration:none; font-weight:600 }
.chmeta .addr a + a::before { content:' · '; color:var(--muted); font-weight:400 }
.chmeta .demo span { font-size:11.4px }
.chmeta .demo u { text-decoration:none; font-weight:700; letter-spacing:0;
  font-variant-numeric:tabular-nums }
.chmeta .demo i { font-style:normal; margin-left:12px; font-size:10.6px;
  color:var(--muted) }

/* 표지 수치는 본문보다 한 단계 크게 */
.chstats.big { margin-top:24px; padding:20px 0 0; border-bottom:0 }
.chstats.big b { font-size:46px; white-space:nowrap }
.chstats.big.sm b { font-size:33px }
.chstats.big span { font-size:11.2px }
"""
