/* 저장·가입 버튼 연속 클릭 방지: 한 번 보내면 버튼을 잠근다 (PRD 8장) */
(function () {
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (e.defaultPrevented) return;
      if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
        e.preventDefault();
        return;
      }
      form.querySelectorAll("button[data-once]").forEach(function (btn) {
        // 버튼을 바로 잠그면 일부 브라우저에서 전송이 취소되므로 다음 순간에 잠근다
        setTimeout(function () { btn.disabled = true; }, 0);
      });
    });
  });
})();
