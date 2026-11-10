/* 랜딩페이지 측정: CTA 클릭, FAQ 열기, 요금 섹션 노출 (PRD F9) */
(function () {
  // 버튼 클릭: 어느 위치의 버튼인지만 보낸다
  document.querySelectorAll("[data-cta]").forEach(function (el) {
    el.addEventListener("click", function () {
      window.track("cta_click", { location: el.dataset.cta });
    });
  });

  // FAQ 질문을 열 때: 질문 번호(Q1~Q8)만 보낸다
  document.querySelectorAll("details[data-faq]").forEach(function (item) {
    item.addEventListener("toggle", function () {
      if (item.open) window.track("faq_open", { question_id: item.dataset.faq });
    });
  });

  // 요금 섹션이 화면에 처음 보일 때 한 번
  var pricing = document.getElementById("pricing");
  if (pricing && "IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        if (entries.some(function (e) { return e.isIntersecting; })) {
          window.track("pricing_view");
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(pricing);
  }
})();
