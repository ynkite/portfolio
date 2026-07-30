/* 분석·설계 문서 뷰어.
   엑셀 캡처를 붙이지 않고, 시트 원본 데이터(docs-*.js)를 이 페이지의 글꼴·브랜드 색으로 다시 그린다.
   상세페이지가 할 일은 두 가지뿐 — docs-*.js를 먼저 불러오고, 버튼에 data-doc="키"를 달아 두는 것. */
(function () {
  'use strict';

  var docs = window.PROJECT_DOCS;
  if (!docs) return;

  // 이 페이지의 브랜드 색을 그대로 쓴다 (COGI 네이비블루 · TripLinker 테라코타 · 오몽 오렌지)
  var css = getComputedStyle(document.documentElement);
  var brand = (css.getPropertyValue('--teal') || css.getPropertyValue('--brand') || '#0066cc').trim();

  var style = document.createElement('style');
  style.textContent = [
    '.docbtns{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:26px}',
    // 눌러서 볼 수 있다는 걸 알려 준다 — 칩 여섯 줄에 마크업을 늘리지 않으려고 CSS로 붙인다
    '.docbtns::before{content:"문서 보기";font-size:12.5px;color:var(--muted);margin-right:2px}',
    '.docbtn{font-family:inherit;font-size:14px;font-weight:600;cursor:pointer;color:inherit;',
    'display:inline-flex;align-items:center;gap:8px;padding:11px 18px;border-radius:980px;',
    'border:1px solid var(--line);background:#fff;transition:transform .3s var(--ease),border-color .3s}',
    '.docbtn:hover{transform:translateY(-2px);border-color:' + brand + ';color:' + brand + '}',
    '.docbtn::before{content:"";width:15px;height:18px;flex:none;border-radius:2px;',
    'background:' + brand + ';opacity:.16}',
    '.dvbg{position:fixed;inset:0;z-index:300;background:rgba(0,0,0,.55);',
    '-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);display:none;padding:26px}',
    '.dvbg.on{display:flex;align-items:center;justify-content:center}',
    '.dv{background:#fff;border-radius:20px;width:100%;max-width:1180px;max-height:100%;',
    'display:flex;flex-direction:column;overflow:hidden;box-shadow:0 50px 110px -30px rgba(0,0,0,.5)}',
    '.dv .hd{display:flex;align-items:flex-start;gap:16px;padding:20px 24px;border-bottom:1px solid var(--line)}',
    '.dv .hd h3{font-size:19px;font-weight:700;letter-spacing:-.02em}',
    '.dv .hd .src{font-size:12px;color:var(--muted);margin-top:3px}',
    '.dv .x{margin-left:auto;flex:none;font-family:inherit;font-size:22px;line-height:1;cursor:pointer;',
    'border:0;background:none;color:var(--muted);padding:2px 6px}',
    '.dv .x:hover{color:var(--ink)}',
    '.dv .bd{overflow:auto;-webkit-overflow-scrolling:touch}',
    '.dv table{border-collapse:collapse;width:100%;font-size:13px}',
    '.dv th,.dv td{border:1px solid var(--line);padding:8px 11px;text-align:left;vertical-align:top;',
    'white-space:pre-wrap;word-break:keep-all;overflow-wrap:break-word}',
    '.dv th{position:sticky;top:0;z-index:1;background:' + brand + ';color:#fff;font-weight:600;',
    'white-space:nowrap;letter-spacing:-.01em}',
    '.dv tbody tr:nth-child(even){background:#fafafc}',
    '.dv tbody tr:hover{background:#f2f7ff}',
    '.dv td:first-child{white-space:nowrap;font-weight:600}',
    '.dv tr.grp td{background:' + brand + '14;color:' + brand + ';font-weight:700;font-size:13.5px;',
    'white-space:pre-wrap;padding:11px 12px}',
    '.dv tr.grp:hover td{background:' + brand + '1f}',
    // WBS 주차 칸 — 원본 엑셀에서 칠해 둔 색을 바로 되살린다
    '.dv td.bar{padding:6px 5px;min-width:78px}',
    '.dv td.bar span{display:block;height:15px;border-radius:8px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}',
    '.dv .ft{padding:12px 24px;border-top:1px solid var(--line);font-size:12px;color:var(--muted)}',
    '.dv .ft .lgd{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px}',
    '.dv .ft .lgd span{display:inline-flex;align-items:center;gap:6px;color:var(--sub);font-weight:600}',
    '.dv .ft .lgd i{width:22px;height:11px;border-radius:6px;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}',
    '.dv .ft .note{margin-top:8px;color:' + brand + ';line-height:1.55}',
    // 상태 값에 배지를 입혀 완료·진행·예정이 한눈에 갈리게 한다
    '.dv td.st{white-space:nowrap;font-weight:600}',
    '.dv td.st.done{color:#0f7a52}',
    '.dv td.st.now{color:#a8620a}',
    '.dv td.st.todo{color:var(--muted)}',
    '@media(max-width:640px){.dvbg{padding:0}.dv{border-radius:0;max-width:none}.dv table{font-size:12px}}'
  ].join('');
  document.head.appendChild(style);

  var bg = document.createElement('div');
  bg.className = 'dvbg';
  bg.innerHTML = '<div class="dv" role="dialog" aria-modal="true" aria-label="문서 보기">' +
    '<div class="hd"><div><h3></h3><div class="src"></div></div>' +
    '<button class="x" aria-label="닫기">&times;</button></div>' +
    '<div class="bd"></div><div class="ft"></div></div>';
  document.body.appendChild(bg);

  var elTitle = bg.querySelector('h3'),
      elSrc = bg.querySelector('.src'),
      elBody = bg.querySelector('.bd'),
      elFoot = bg.querySelector('.ft');

  function cell(tag, text) {
    var td = document.createElement(tag);
    td.textContent = text;           // 시트 값은 그대로 텍스트로만 넣는다
    return td;
  }

  function open(key) {
    var d = docs[key];
    if (!d) return;
    elTitle.textContent = d.label;
    elSrc.textContent = d.file + '  ·  시트 「' + d.sheet + '」';
    elFoot.textContent = '';
    var base = document.createElement('div');
    base.textContent = d.rows.length + '행 — 프로젝트 산출 문서를 이 페이지 서식으로 다시 그린 것입니다.';
    elFoot.appendChild(base);
    if (d.legend) {                              // WBS 색 = 담당자
      var lg = document.createElement('div');
      lg.className = 'lgd';
      d.legend.forEach(function (it) {
        var chip = document.createElement('span');
        var sw = document.createElement('i');
        sw.style.background = it.color;
        chip.appendChild(sw);
        chip.appendChild(document.createTextNode(it.who));
        lg.appendChild(chip);
      });
      elFoot.appendChild(lg);
    }
    if (d.note) {                                // 원본을 손댄 부분은 밝혀 둔다
      var nt = document.createElement('div');
      nt.className = 'note';
      nt.textContent = d.note;
      elFoot.appendChild(nt);
    }

    var table = document.createElement('table'), thead = document.createElement('thead'),
        tbody = document.createElement('tbody'), tr = document.createElement('tr');
    d.head.forEach(function (h, i) { tr.appendChild(cell('th', h || '·')); });
    thead.appendChild(tr);
    d.rows.forEach(function (r) {
      var row = document.createElement('tr');
      if (r && r.g !== undefined) {              // 문서 중간의 그룹 머리행 (테이블명·단계 등)
        row.className = 'grp';
        var td = cell('td', r.g);
        td.colSpan = d.head.length;
        row.appendChild(td);
      } else {
        // WBS는 일정을 셀 색으로 칠해 둔다 — 그 색을 주차 칸의 바로 되살린다
        var cells = r.c || r, bars = r.b || null;
        for (var i = 0; i < d.head.length; i++) {
          var td2 = cell('td', cells[i] || '');
          var st = { '완료': 'done', '진행': 'now', '예정': 'todo' }[cells[i]];
          if (st) td2.className = 'st ' + st;
          if (bars && bars[i]) {
            td2.className = 'bar';
            var span = document.createElement('span');
            span.style.background = bars[i];
            td2.appendChild(span);
          }
          row.appendChild(td2);
        }
      }
      tbody.appendChild(row);
    });
    table.appendChild(thead); table.appendChild(tbody);
    elBody.textContent = '';
    elBody.appendChild(table);
    elBody.scrollTop = 0;
    bg.classList.add('on');
    document.body.style.overflow = 'hidden';
    bg.querySelector('.x').focus();
  }

  function close() {
    bg.classList.remove('on');
    document.body.style.overflow = '';
    elBody.textContent = '';        // 큰 표를 열어둔 채 방치하지 않는다
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-doc]');
    if (b) { open(b.getAttribute('data-doc')); return; }
    if (e.target === bg || e.target.closest('.x')) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && bg.classList.contains('on')) close();
  });
})();
