"""로그인 없이 볼 수 있는 화면: 랜딩, 개인정보처리방침, 이용약관, 위기 안내. 검색엔진용 robots.txt·sitemap.xml."""

from flask import Blueprint, Response, current_app, render_template, send_from_directory, url_for

import content
from db import get_db

bp = Blueprint("pages", __name__)

# PRD v5 F10: 색인 대상 공개 화면 5개. 이 밖의 HTML 화면은 모두 noindex (base.html)
INDEXABLE_ENDPOINTS = (
    "pages.landing",
    "pages.try_write",
    "pages.help_page",
    "pages.privacy",
    "pages.terms",
)
# 로그인이 필요한 화면 경로 (robots.txt에서 막는다)
PRIVATE_PATHS = ("/drawer", "/reflect", "/settings")


def load_choices():
    """감정·욕구 목록은 코드가 아닌 DB에서 읽는다."""
    conn = get_db()
    emotions = conn.execute("SELECT code, label FROM emotions ORDER BY sort_order").fetchall()
    needs = conn.execute("SELECT code, label FROM needs ORDER BY sort_order").fetchall()
    return emotions, needs


@bp.get("/")
def landing():
    # 주소는 코드에 쓰지 않고 접속한 주소로 만든다 (배포에서는 TRUST_PROXY로 https)
    site_url = url_for("pages.landing", _external=True)
    org_jsonld = content.organization_jsonld(
        site_url=site_url,
        logo_url=url_for("static", filename="img/favicon.svg", _external=True),
    )
    return render_template(
        "landing.html",
        c=content,
        faq_jsonld=content.faq_jsonld(),
        org_jsonld=org_jsonld,
        website_jsonld=content.website_jsonld(site_url),
    )


@bp.get("/robots.txt")
def robots_txt():
    """F10-1: 모든 크롤러 허용, 로그인 필요 경로만 막는다.
    /login·/signup은 막지 않는다 (막으면 크롤러가 화면의 noindex를 읽지 못한다)."""
    lines = ["User-agent: *", "Allow: /"]
    lines += [f"Disallow: {path}" for path in PRIVATE_PATHS]
    lines += ["", "Sitemap: " + url_for("pages.sitemap_xml", _external=True), ""]
    return Response("\n".join(lines), mimetype="text/plain")


@bp.get("/sitemap.xml")
def sitemap_xml():
    """F10-2: 색인 대상 공개 화면 5개만. 수정 날짜(lastmod)는 정확히 알 수 없어 넣지 않는다."""
    urls = "".join(
        f"  <url><loc>{url_for(endpoint, _external=True)}</loc></url>\n"
        for endpoint in INDEXABLE_ENDPOINTS
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")


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
