"""회원: 가입·로그인·로그아웃과 로그인 확인 장치 (PRD F3)."""

import functools
import re

from flask import (Blueprint, g, redirect, render_template, request, session,
                   url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import content
from db import get_db, now_iso
from plans import trial_end_from_now

bp = Blueprint("auth", __name__)

A = content.AUTH
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# 쓰던 기록을 이어서 담을 수 있는 화면 (로그인 만료 안내용)
WRITE_PATH_RE = re.compile(r"^/drawer/(new|\d+/edit)$")
# 브라우저 임시 보관본 이름 (로그아웃·저장 완료 시 지운다)
WRITE_DRAFT_PREFIXES = ["ed_write_draft", "ed_edit_draft_"]


# ---------- 공통 ----------
def load_logged_in_user():
    """매 요청마다 로그인한 사용자를 g.user 에 넣는다."""
    user_id = session.get("uid")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if g.user is None:  # 삭제된 계정
            session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def safe_next(value):
    """로그인 후 돌아갈 주소는 이 사이트 안의 주소만 허용한다."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return None


def queue_ga_event(name, params=None):
    """서버에서 일어난 일(가입·저장)을 다음 화면에서 GA4로 한 번 보낸다. 내용 없는 값만 넣을 것."""
    events = session.get("ga_events", [])
    events.append({"name": name, "params": params or {}})
    session["ga_events"] = events


def queue_clear_drafts(prefixes):
    """다음 화면에서 브라우저 임시 보관본을 지운다."""
    session["clear_drafts"] = list(prefixes)


def start_session(user_id):
    session.clear()
    session.permanent = True  # 로그인 유지 7일 (config)
    session["uid"] = user_id


# ---------- 가입 ----------
@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if g.user is not None:
        return redirect(url_for("drawer.index"))

    form = {"email": "", "nickname": "", "marketing": False,
            "from_try": request.values.get("from") == "try"}
    errors = {}

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password2 = request.form.get("password_confirm", "")
        nickname = request.form.get("nickname", "").strip()
        agree = request.form.get("agree") == "on"
        marketing = request.form.get("marketing") == "on"
        form.update(email=email, nickname=nickname, marketing=marketing)

        if not EMAIL_RE.match(email) or len(email) > 254:
            errors["email"] = A["email_invalid"]
        if len(password) < 8 or not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            errors["password"] = A["password_rule"]
        elif password != password2:
            errors["password_confirm"] = A["password_mismatch"]
        if not 2 <= len(nickname) <= 12:
            errors["nickname"] = A["nickname_rule"]
        if not agree:
            errors["agree"] = A["agree_required"]

        conn = get_db()
        if "email" not in errors and conn.execute(
            "SELECT 1 FROM users WHERE email = ?", (email,)
        ).fetchone():
            errors["email"] = A["email_taken"]

        if not errors:
            now = now_iso()
            cur = conn.execute(
                """INSERT INTO users (email, password_hash, nickname, marketing_consent,
                       marketing_consent_at, plus_trial_ends_at, created_at, last_visit_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (email, generate_password_hash(password), nickname, int(marketing),
                 now if marketing else None, trial_end_from_now(), now, now),
            )
            conn.commit()
            start_session(cur.lastrowid)
            queue_ga_event("sign_up", {"from_try": form["from_try"]})
            # 가입 직후 내 서랍에서 체험 기록 보관 여부를 묻는다 (F2-10)
            session["offer_try_import"] = True
            return redirect(url_for("drawer.index"))

    return render_template("auth/signup.html", c=content, form=form, errors=errors), (400 if errors else 200)


# ---------- 로그인 ----------
@bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = safe_next(request.values.get("next"))
    if g.user is not None:
        return redirect(next_url or url_for("drawer.index"))

    error = None
    email = ""
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        # 이메일이 없을 때와 비밀번호가 틀릴 때 같은 문구 (F3-4)
        if user is None or not check_password_hash(user["password_hash"], password):
            error = A["login_failed"]
        else:
            conn.execute("UPDATE users SET last_visit_at = ? WHERE id = ?", (now_iso(), user["id"]))
            conn.commit()
            start_session(user["id"])
            return redirect(next_url or url_for("drawer.index"))

    resume_notice = content.MESSAGES["session_expired"] if next_url and WRITE_PATH_RE.match(next_url) else None
    return render_template(
        "auth/login.html", c=content, error=error, email=email,
        next_url=next_url, resume_notice=resume_notice,
    ), (400 if error else 200)


# ---------- 로그아웃 ----------
@bp.post("/logout")
def logout():
    session.clear()
    # 같은 기기를 쓰는 다른 사람이 보지 않도록 작성 중 임시 보관본을 지운다 (F2-11)
    queue_clear_drafts(WRITE_DRAFT_PREFIXES)
    return redirect(url_for("pages.landing"))
