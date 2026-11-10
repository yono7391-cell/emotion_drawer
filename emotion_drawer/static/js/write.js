/*
 * 4단계 기록 화면 (PRD F2)
 * 시작(감정 하나 고르기) → 1 상황 → 2 생각 → 3 감정 → 4 욕구 → 마무리
 *
 * - 입력 내용은 브라우저(localStorage)에만 임시 보관한다. try 모드에서는 서버로 아무것도 보내지 않는다.
 * - 체험 임시 보관본은 24시간이 지나면 지운다 (F2-9).
 * - GA4 이벤트에는 단계 번호만 보내고, 기록 내용·감정 이름은 절대 보내지 않는다.
 */
(function () {
  "use strict";

  var form = document.getElementById("write-form");
  if (!form) return;
  form.hidden = false; // 자바스크립트가 켜져 있을 때만 보인다

  var MODE = form.dataset.mode;               // try | new | edit
  var DRAFT_KEY = form.dataset.draftKey;
  var DRAFT_TTL_MS = 24 * 60 * 60 * 1000;
  var MAX_EMOTIONS = 3;
  var MAX_TEXT = 1000;
  // 수정은 기존 값이 있으므로 '감정 하나 고르기'를 건너뛰고 1단계부터 (F4-6)
  var ORDER = MODE === "edit" ? ["1", "2", "3", "4", "finish"] : ["start", "1", "2", "3", "4", "finish"];
  var FIRST = ORDER[0];
  var STEP_NO = { "1": 1, "2": 2, "3": 3, "4": 4 };
  var MSG = JSON.parse(document.getElementById("write-messages").textContent);

  var alertEl = form.querySelector("[data-alert]");
  var progressEl = form.querySelector("[data-progress]");
  var progressText = form.querySelector("[data-progress-text]");
  var progressBars = form.querySelectorAll(".progress__bar span");
  var prevBtn = form.querySelector('[data-action="prev"]');
  var startNextBtn = form.querySelector("[data-requires-start]");

  var saveBtn = form.querySelector('[data-action="save"]');
  var dateInput = form.elements.entry_date || null;

  var state = { step: FIRST, autoEmotion: null, completedTracked: false };

  function track(name, params) {
    if (MODE === "try" && typeof window.track === "function") window.track(name, params);
  }

  // ---------- 임시 보관 ----------
  var storage = (function () {
    try {
      var k = "__ed_storage_test";
      window.localStorage.setItem(k, "1");
      window.localStorage.removeItem(k);
      return window.localStorage;
    } catch (e) {
      return null; // 사생활 보호 모드 등
    }
  })();

  function readDraft() {
    if (!storage) return null;
    try {
      var raw = storage.getItem(DRAFT_KEY);
      if (!raw) return null;
      var draft = JSON.parse(raw);
      var expired = !draft.savedAt || Date.now() - draft.savedAt > DRAFT_TTL_MS;
      if (MODE === "try" && expired) {
        storage.removeItem(DRAFT_KEY);
        return null;
      }
      return draft;
    } catch (e) {
      return null;
    }
  }

  function clearDraft() {
    if (!storage) return;
    try { storage.removeItem(DRAFT_KEY); } catch (e) { /* 무시 */ }
  }

  function isEmpty(d) {
    return !d.startEmotion && !d.situation && !d.thought && !d.emotions.length &&
      !d.intensity && !d.needCode && !d.needNote;
  }

  function saveDraft() {
    clearTimeout(saveTimer);
    savePending = false;
    if (!storage || discarded) return;
    // 작성·수정은 사용자가 무언가 바꿨을 때만 남긴다 (열어 보기만 한 기록이 남지 않도록)
    if (MODE !== "try" && !dirty) return;
    var data = collect();
    try {
      if (state.step === "start" && isEmpty(data)) {
        storage.removeItem(DRAFT_KEY); // 아무것도 안 했으면 남기지 않는다
        return;
      }
      storage.setItem(DRAFT_KEY, JSON.stringify({
        savedAt: Date.now(),
        step: state.step,
        autoEmotion: state.autoEmotion,
        completedTracked: state.completedTracked,
        data: data
      }));
    } catch (e) { /* 저장 공간 부족 등: 무시 */ }
  }

  var saveTimer = null;
  var savePending = false;  // 아직 저장하지 않은 입력이 있는지
  var discarded = false;    // [그냥 닫기]로 버린 뒤에는 다시 저장하지 않는다
  var dirty = false;        // 이 화면에서 입력을 바꿨는지
  function saveSoon() {
    dirty = true;
    clearTimeout(saveTimer);
    savePending = true;
    saveTimer = setTimeout(saveDraft, 300);
  }

  // ---------- 값 읽기·쓰기 ----------
  function inputs(name) {
    return form.querySelectorAll('input[name="' + name + '"]');
  }

  function checked(name) {
    return Array.prototype.filter.call(inputs(name), function (i) { return i.checked; })
      .map(function (i) { return i.value; });
  }

  function setChecked(name, values) {
    inputs(name).forEach(function (i) { i.checked = values.indexOf(i.value) !== -1; });
  }

  function collect() {
    var intensity = checked("intensity")[0];
    return {
      startEmotion: checked("start_emotion")[0] || null,
      situation: form.elements.situation.value,
      thought: form.elements.thought.value,
      emotions: checked("emotions"),
      intensity: intensity ? Number(intensity) : null,
      needCode: checked("need_code")[0] || null,
      needNote: form.elements.need_note.value,
      entryDate: dateInput ? dateInput.value : null
    };
  }

  function restore(d) {
    setChecked("start_emotion", d.startEmotion ? [d.startEmotion] : []);
    form.elements.situation.value = String(d.situation || "").slice(0, MAX_TEXT);
    form.elements.thought.value = String(d.thought || "").slice(0, MAX_TEXT);
    setChecked("emotions", (d.emotions || []).slice(0, MAX_EMOTIONS));
    setChecked("intensity", d.intensity ? [String(d.intensity)] : []);
    setChecked("need_code", d.needCode ? [d.needCode] : []);
    form.elements.need_note.value = String(d.needNote || "").slice(0, MAX_TEXT);
    if (dateInput && d.entryDate) dateInput.value = d.entryDate;
  }

  function labelOf(name, value) {
    var found = Array.prototype.find.call(inputs(name), function (i) { return i.value === value; });
    return found ? found.nextElementSibling.textContent : "";
  }

  // ---------- 안내 문구 ----------
  function say(message) {
    alertEl.textContent = message || "";
  }

  function updateCounter(textarea) {
    var counter = form.querySelector('[data-counter-for="' + textarea.name + '"]');
    if (!counter) return;
    var len = textarea.value.length;
    counter.textContent = len + " / " + MAX_TEXT;
    counter.classList.toggle("is-full", len >= MAX_TEXT);
    if (len >= MAX_TEXT) say(MSG.text_max);
  }

  function updateStartNext() {
    if (startNextBtn) startNextBtn.disabled = checked("start_emotion").length === 0;
  }

  // ---------- 시작에서 고른 감정을 3단계에 미리 선택 (F2-1) ----------
  function applyStartEmotion() {
    var start = checked("start_emotion")[0];
    if (!start) return;
    var emotions = checked("emotions");
    // 시작 감정을 바꿨다면, 예전에 자동으로 넣었던 감정은 뺀다
    if (state.autoEmotion && state.autoEmotion !== start) {
      emotions = emotions.filter(function (code) { return code !== state.autoEmotion; });
    }
    if (emotions.indexOf(start) === -1 && emotions.length < MAX_EMOTIONS) emotions.push(start);
    setChecked("emotions", emotions);
    state.autoEmotion = start;
  }

  // ---------- 마무리 요약 ----------
  function setSummary(key, value) {
    form.querySelector('[data-summary="' + key + '"]').textContent = value || "—";
  }

  function renderSummary() {
    var d = collect();
    setSummary("situation", d.situation.trim());
    setSummary("thought", d.thought.trim());
    var emotionText = d.emotions.map(function (c) { return labelOf("emotions", c); }).join(" · ");
    if (emotionText && d.intensity) emotionText += " (" + d.intensity + " / 5)";
    setSummary("emotions", emotionText);
    var needText = [d.needCode ? labelOf("need_code", d.needCode) : "", d.needNote.trim()]
      .filter(Boolean).join(" — ");
    setSummary("need", needText);
  }

  // ---------- 단계 이동 ----------
  function show(step, moveFocus) {
    state.step = step;
    form.dataset.current = step;
    form.querySelectorAll(".write__step").forEach(function (el) {
      el.hidden = el.dataset.step !== step;
    });
    prevBtn.hidden = step === FIRST;

    var no = STEP_NO[step];
    progressEl.hidden = !no;
    if (no) {
      progressText.textContent = no + " / 4";
      progressBars.forEach(function (bar, i) { bar.classList.toggle("is-done", i < no); });
    }

    if (step === "finish") {
      renderSummary();
      if (!state.completedTracked) {
        track("try_complete");
        state.completedTracked = true;
      }
    }

    say("");
    updateStartNext();
    saveDraft();

    if (moveFocus !== false) {
      var title = form.querySelector('[data-step="' + step + '"] .write__title');
      if (title) title.focus({ preventScroll: true });
      window.scrollTo(0, 0); // 제목이 상단 고정 머리말에 가려지지 않도록 맨 위로
    }
  }

  function go(delta) {
    var i = ORDER.indexOf(state.step);
    var next = ORDER[Math.max(0, Math.min(ORDER.length - 1, i + delta))];
    if (state.step === "start" && delta > 0) applyStartEmotion();
    show(next);
  }

  // ---------- 이벤트 ----------
  // 강도: 이미 고른 숫자를 다시 누르면 선택 해제
  form.addEventListener("pointerdown", function (e) {
    var item = e.target.closest(".scale__item");
    if (item) {
      var input = item.querySelector("input");
      input.dataset.wasChecked = input.checked ? "1" : "";
    }
  });

  form.addEventListener("click", function (e) {
    var t = e.target;
    if (t.name === "intensity" && t.dataset.wasChecked === "1") {
      t.checked = false;
      t.dataset.wasChecked = "";
      saveSoon();
      return;
    }

    var btn = t.closest("[data-action]");
    if (!btn) return;
    var action = btn.dataset.action;

    if (action === "next") {
      if (STEP_NO[state.step]) track("try_step_complete", { step: STEP_NO[state.step] });
      go(1);
    } else if (action === "skip") {
      go(1);
    } else if (action === "prev") {
      go(-1);
    } else if (action === "restart") {
      clearDraft();
      form.reset();
      state = { step: "start", autoEmotion: null, completedTracked: false };
      form.querySelectorAll("textarea").forEach(updateCounter);
      show("start");
    } else if (action === "close") {
      discarded = true;
      clearDraft();
      window.location.href = "/";
    } else if (action === "keep") {
      // 저장 최소 조건: 감정 1개 이상 (F2-3, 8장)
      if (checked("emotions").length === 0) {
        e.preventDefault();
        show("3");
        say(MSG.emotion_required);
      } else {
        saveDraft(); // 가입 후 보관할 수 있도록 최신 내용을 남겨 둔다
      }
    }
  });

  form.addEventListener("change", function (e) {
    var t = e.target;
    if (t.name === "emotions") {
      if (t.checked && checked("emotions").length > MAX_EMOTIONS) {
        t.checked = false; // 4번째 선택 막음
        say(MSG.emotion_max);
      } else {
        say("");
      }
    }
    if (t.name === "need_code" && t.checked) {
      // 욕구는 1개만
      inputs("need_code").forEach(function (i) { if (i !== t) i.checked = false; });
    }
    if (t.name === "start_emotion") updateStartNext();
    saveSoon();
  });

  form.addEventListener("input", function (e) {
    if (e.target.tagName === "TEXTAREA") updateCounter(e.target);
    saveSoon();
  });

  form.addEventListener("submit", function (e) {
    if (MODE === "try") {
      e.preventDefault(); // 체험은 절대 서버로 보내지 않는다
      return;
    }
    // 저장 최소 조건: 감정 1개 이상 (F2-3, 8장)
    if (checked("emotions").length === 0) {
      e.preventDefault();
      show("3");
      say(MSG.emotion_required);
      return;
    }
    // 저장이 실패(로그인 만료 등)해도 다시 이어 쓸 수 있도록 최신 내용을 남겨 둔다.
    // 저장에 성공하면 서버가 다음 화면에서 이 임시 보관본을 지운다.
    dirty = true;
    saveDraft();
    // 연속 클릭 방지 (전송이 시작된 다음 순간에 잠근다)
    if (saveBtn) setTimeout(function () { saveBtn.disabled = true; }, 0);
  });

  // 떠나기 직전에 아직 저장하지 않은 입력만 마저 저장
  window.addEventListener("pagehide", function () {
    if (savePending) saveDraft();
  });

  // ---------- 시작 ----------
  // 서버가 검사 실패로 다시 보여 준 화면이면, 서버가 채운 값과 단계·안내를 그대로 쓴다
  var serverStep = form.dataset.initialStep;
  var draft = serverStep ? null : readDraft();
  if (draft) {
    restore(draft.data || {});
    state.autoEmotion = draft.autoEmotion || null;
    state.completedTracked = !!draft.completedTracked;
    dirty = true; // 복구한 내용은 계속 임시 보관
  } else {
    track("try_start");
  }
  form.querySelectorAll("textarea").forEach(function (ta) {
    var counter = form.querySelector('[data-counter-for="' + ta.name + '"]');
    if (counter) counter.textContent = ta.value.length + " / " + MAX_TEXT;
  });
  var firstStep = serverStep || (draft && draft.step) || FIRST;
  show(ORDER.indexOf(firstStep) !== -1 ? firstStep : FIRST, false);
  if (form.dataset.initialAlert) say(form.dataset.initialAlert);
  else if (!storage) say(MSG.storage_unavailable);
})();
