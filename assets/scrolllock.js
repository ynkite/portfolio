/* 팝업이 떠 있는 동안 뒤 페이지가 움직이지 않게 잠근다.
 *
 * 왜 따로 두는가 — 원래는 팝업을 열 때 `document.body.style.overflow = 'hidden'` 만 걸었다.
 * 그런데 이 사이트의 스크롤 컨테이너는 body 가 아니라 html 이다(html 에 scroll-snap 이 걸려 있다).
 * body 에 걸어도 아무 일이 일어나지 않아서, 팝업 밖에서 휠을 굴리면 뒤 페이지가 따라 움직였다.
 * 그래서 html 에 같이 걸고, 풀 때 스크롤 위치를 되돌려 준다.
 *
 * 팝업이 겹쳐 열릴 수 있으므로(문서 뷰어 위에 이미지 확대) 잠금 횟수를 센다.
 * 안쪽에서 하나 닫았다고 풀어 버리면 바깥 팝업이 열려 있는데도 뒤가 움직인다.
 */
(function () {
  var depth = 0;
  var savedY = 0;

  window.lockScroll = function () {
    if (depth++ > 0) return;
    var d = document.documentElement;
    savedY = window.scrollY || d.scrollTop || 0;
    // 스크롤바가 사라지면서 지면 폭이 튀는 것을 막는다
    var pad = window.innerWidth - d.clientWidth;
    d.style.overflow = 'hidden';
    document.body.style.overflow = 'hidden';
    if (pad > 0) document.body.style.paddingRight = pad + 'px';
  };

  window.unlockScroll = function () {
    if (depth === 0) return;
    if (--depth > 0) return;
    var d = document.documentElement;
    d.style.overflow = '';
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    // overflow 를 되돌리면 브라우저가 스크롤을 되감는 경우가 있다.
    // 부드러운 스크롤이 걸려 있으면 되돌리는 과정이 눈에 보이므로 잠깐 끈다
    var prev = d.style.scrollBehavior;
    d.style.scrollBehavior = 'auto';
    window.scrollTo(0, savedY);
    d.style.scrollBehavior = prev;
  };
})();
