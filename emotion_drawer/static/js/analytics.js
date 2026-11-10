/*
 * GA4 이벤트 보내기 도우미.
 * - .env 에 측정 ID가 없으면 GA4 스크립트가 없어서(gtag 없음) 아무것도 보내지 않는다.
 * - 매개변수에 기록 내용, 감정 이름, 이메일을 절대 넣지 않는다.
 */
(function () {
  window.track = function (name, params) {
    if (typeof window.gtag !== "function") return;
    window.gtag("event", name, params || {});
  };
})();
