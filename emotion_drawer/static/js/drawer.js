/*
 * 가입 직후 "체험에서 쓴 기록을 첫 기록으로 보관할까요?" (PRD F2-10)
 * - 브라우저에 24시간 안의 체험 기록(감정 1개 이상)이 있을 때만 묻는다.
 * - [보관하기]를 눌렀을 때만 서버로 보낸다. 어느 쪽을 눌러도 브라우저 임시 보관본은 지운다.
 */
(function () {
  "use strict";

  var KEY = "ed_try_draft";
  var TTL_MS = 24 * 60 * 60 * 1000;
  var box = document.querySelector("[data-import-offer]");
  if (!box) return;

  var storage;
  try { storage = window.localStorage; } catch (e) { return; }

  function removeDraft() {
    try { storage.removeItem(KEY); } catch (e) { /* 무시 */ }
  }

  var draft = null;
  try { draft = JSON.parse(storage.getItem(KEY) || "null"); } catch (e) { draft = null; }

  var usable = draft && draft.data && draft.savedAt && (Date.now() - draft.savedAt <= TTL_MS) &&
    Array.isArray(draft.data.emotions) && draft.data.emotions.length > 0;
  if (!usable) {
    removeDraft(); // 보관할 수 없는(빈·만료된) 체험 기록은 정리만 한다
    return;
  }

  box.hidden = false;
  var alertEl = box.querySelector("[data-import-alert]");
  var buttons = box.querySelectorAll("button");

  box.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-import]");
    if (!btn) return;

    if (btn.dataset.import === "no") {
      removeDraft();
      box.hidden = true;
      return;
    }

    buttons.forEach(function (b) { b.disabled = true; });
    fetch(box.dataset.url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": box.dataset.csrf },
      body: JSON.stringify(draft.data)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (body) {
        if (res.ok) {
          removeDraft();
          window.location.reload();
        } else {
          alertEl.textContent = body.error || "";
          buttons.forEach(function (b) { b.disabled = false; });
        }
      });
    }).catch(function () {
      buttons.forEach(function (b) { b.disabled = false; });
    });
  });
})();
