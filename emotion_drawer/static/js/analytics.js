/*
 * 측정 이벤트 보내기 도우미 (PRD v4 F9).
 * - 이벤트를 GTM의 dataLayer에 { event: 이름, ...매개변수 } 형태로 넣는다. GA4로 보내는 설정은 GTM 컨테이너에서 한다.
 * - .env 에 GTM 컨테이너 ID가 없으면 GTM 스크립트가 없어서(dataLayer 없음) 아무것도 보내지 않는다.
 * - 매개변수에 기록 내용, 감정 이름, 이메일을 절대 넣지 않는다.
 */
(function () {
  window.track = function (name, params) {
    if (!window.dataLayer || typeof window.dataLayer.push !== "function") return;
    var data = { event: name };
    var p = params || {};
    Object.keys(p).forEach(function (key) { data[key] = p[key]; });
    window.dataLayer.push(data);
  };
})();
