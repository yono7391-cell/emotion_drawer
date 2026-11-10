"""내 서랍: 기록 목록·상세·작성·수정·삭제·체험 보관 (PRD F2-10, F2-11, F4).

- 모든 화면은 로그인이 필요하다.
- 기록은 항상 'id 와 user_id 가 함께 맞을 때만' 찾는다. 아니면 404 "기록을 찾을 수 없어요."
- 감정 필터와 키워드 검색 조건은 주소(URL)에 넣지 않고 세션에 보관한다
  (감정 이름·검색어가 주소창, 서버 로그, GA4 페이지 주소에 남지 않도록).
"""

from flask import (Blueprint, abort, g, jsonify, redirect, render_template,
                   request, session, url_for)

import content
import entries
from auth import login_required, queue_clear_drafts, queue_ga_event
from db import get_db, today_kst
from pages import load_choices
from plans import plan_status

bp = Blueprint("drawer", __name__, url_prefix="/drawer")

D = content.DRAWER
PAGE_SIZE = 20
MAX_PAGES = 50
KEYWORD_MAX = 50


def _not_found():
    return render_template("errors/404.html", message=D["not_found"]), 404


def _filter_state():
    f = session.get("drawer_filter") or {}
    return {"emotion": f.get("emotion"), "q": f.get("q")}


def _render_write(mode, entry=None, error=None, initial_step=None, entry_id=None):
    emotions, needs = load_choices()
    draft_key = "ed_write_draft" if mode == "new" else f"ed_edit_draft_{entry_id}"
    action = url_for("drawer.new") if mode == "new" else url_for("drawer.edit", entry_id=entry_id)
    return render_template(
        "write.html", c=content, mode=mode, draft_key=draft_key, action=action,
        emotions=emotions, needs=needs, entry=entry, error=error,
        initial_step=initial_step, today=today_kst().isoformat(),
    ), (400 if error else 200)


def _entry_from_form(form):
    """검사에 실패했을 때 쓴 내용을 그대로 다시 보여 주기 위한 값."""
    raw = entries.from_form(form)
    return {
        "situation": raw["situation"] or "", "thought": raw["thought"] or "",
        "need_note": raw["need_note"] or "",
        "emotions": [{"code": c} for c in raw["emotions"]],
        "intensity": int(raw["intensity"]) if (raw["intensity"] or "").isdigit() else None,
        "need_code": raw["need_code"], "entry_date": raw["entry_date"] or today_kst().isoformat(),
    }


# ---------- 목록 ----------
@bp.get("")
@login_required
def index():
    conn = get_db()
    plan = plan_status(g.user)
    filt = _filter_state()
    keyword = filt["q"] if plan["is_plus"] else None  # Plus가 아니면 서버에서 검색어를 쓰지 않는다

    try:
        page = max(1, min(MAX_PAGES, int(request.args.get("page", 1))))
    except ValueError:
        page = 1

    rows, has_more = entries.list_for_user(
        conn, g.user["id"], emotion=filt["emotion"], keyword=keyword, limit=PAGE_SIZE * page)
    total = entries.count_for_user(conn, g.user["id"])
    emotions, _needs = load_choices()

    return render_template(
        "drawer/list.html", c=content, rows=rows, has_more=has_more, next_page=page + 1,
        total=total, emotions=emotions, filt=filt, plan=plan,
        search_locked=bool(filt["q"]) and not plan["is_plus"],
        offer_import=session.pop("offer_try_import", False),
        short_date=entries.short_date, first_line=entries.first_line,
    )


@bp.post("/filter")
@login_required
def set_filter():
    if request.form.get("reset"):
        session.pop("drawer_filter", None)
        return redirect(url_for("drawer.index"))

    conn = get_db()
    emotion = request.form.get("emotion") or None
    if emotion and not conn.execute("SELECT 1 FROM emotions WHERE code = ?", (emotion,)).fetchone():
        emotion = None
    q = (request.form.get("q") or "").strip()[:KEYWORD_MAX] or None
    if q and not plan_status(g.user)["is_plus"]:
        q = None  # Plus 기능: 서버에서도 막는다 (F6-4)
    session["drawer_filter"] = {"emotion": emotion, "q": q}
    return redirect(url_for("drawer.index"))


# ---------- 상세 ----------
@bp.get("/<int:entry_id>")
@login_required
def detail(entry_id):
    entry = entries.get(get_db(), g.user["id"], entry_id)
    if entry is None:
        return _not_found()
    return render_template(
        "drawer/detail.html", c=content, entry=entry,
        long_date=entries.long_date,
    )


# ---------- 작성 ----------
@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "GET":
        return _render_write("new")

    conn = get_db()
    try:
        cleaned = entries.validate(conn, entries.from_form(request.form))
    except entries.EntryError as e:
        step = "3" if str(e) in (content.MESSAGES["emotion_required"], content.MESSAGES["emotion_max"]) else "finish"
        return _render_write("new", entry=_entry_from_form(request.form), error=str(e), initial_step=step)

    entry_id, is_first = entries.create(conn, g.user["id"], cleaned)
    queue_ga_event("entry_create", {"is_first": is_first})
    queue_clear_drafts(["ed_write_draft"])
    return redirect(url_for("drawer.detail", entry_id=entry_id))


# ---------- 수정 ----------
@bp.route("/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit(entry_id):
    conn = get_db()
    entry = entries.get(conn, g.user["id"], entry_id)
    if entry is None:
        return _not_found()

    if request.method == "GET":
        return _render_write("edit", entry=entry, entry_id=entry_id)

    try:
        cleaned = entries.validate(conn, entries.from_form(request.form))
    except entries.EntryError as e:
        step = "3" if str(e) in (content.MESSAGES["emotion_required"], content.MESSAGES["emotion_max"]) else "finish"
        return _render_write("edit", entry=_entry_from_form(request.form), error=str(e),
                             initial_step=step, entry_id=entry_id)

    if not entries.update(conn, g.user["id"], entry_id, cleaned):
        return _not_found()
    queue_clear_drafts([f"ed_edit_draft_{entry_id}"])
    return redirect(url_for("drawer.detail", entry_id=entry_id))


# ---------- 삭제 ----------
@bp.post("/<int:entry_id>/delete")
@login_required
def remove(entry_id):
    if not entries.delete(get_db(), g.user["id"], entry_id):
        return _not_found()
    return redirect(url_for("drawer.index"))


# ---------- 체험 기록 보관 (F2-10) ----------
@bp.post("/import-try")
def import_try():
    # 사용자가 [보관하기]를 눌렀을 때만 브라우저가 보낸다
    if g.user is None:
        return jsonify(error="login_required"), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400)
    conn = get_db()
    try:
        cleaned = entries.validate(conn, entries.from_try_json(data), allow_date=False)
    except entries.EntryError as e:
        return jsonify(error=str(e)), 400
    entry_id, is_first = entries.create(conn, g.user["id"], cleaned)
    queue_ga_event("entry_create", {"is_first": is_first})
    return jsonify(ok=True, id=entry_id), 201
