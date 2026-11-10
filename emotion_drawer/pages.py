"""로그인 없이 볼 수 있는 화면: 랜딩, 개인정보처리방침, 이용약관, 위기 안내."""

from flask import Blueprint, current_app, render_template, send_from_directory

import content
from db import get_db

bp = Blueprint("pages", __name__)


def load_choices():
    """감정·욕구 목록은 코드가 아닌 DB에서 읽는다."""
    conn = get_db()
    emotions = conn.execute("SELECT code, label FROM emotions ORDER BY sort_order").fetchall()
    needs = conn.execute("SELECT code, label FROM needs ORDER BY sort_order").fetchall()
    return emotions, needs


@bp.get("/")
def landing():
    return render_template("landing.html", c=content, faq_jsonld=content.faq_jsonld())


@bp.get("/try")
def try_write():
    """가입 없이 해보는 4단계 체험. 입력 내용은 서버로 보내지 않는다 (브라우저에만 임시 보관)."""
    emotions, needs = load_choices()
    return render_template(
        "write.html",
        c=content,
        mode="try",
        draft_key="ed_try_draft",
        emotions=emotions,
        needs=needs,
    )


@bp.get("/favicon.ico")
def favicon():
    """브라우저가 자동으로 찾는 탭 아이콘 (없으면 404가 계속 쌓인다)."""
    return send_from_directory(current_app.static_folder + "/img", "favicon.svg", mimetype="image/svg+xml")


@bp.get("/privacy")
def privacy():
    return render_template("privacy.html")


@bp.get("/terms")
def terms():
    return render_template("terms.html")


@bp.get("/help")
def help_page():
    return render_template("help.html", c=content)
