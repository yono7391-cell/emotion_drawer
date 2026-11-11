"""감정서랍 Flask 앱. 실행: python app.py → http://localhost:5000"""

import secrets

from flask import Flask, g, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect

import content
import db
from config import Config

csrf = CSRFProtect()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning(
            ".env에 SECRET_KEY가 없어 임시 키를 사용합니다. 서버를 다시 켜면 로그인이 풀립니다."
        )
    if not Config.DATABASE.exists():
        # 배포 환경에서는 Volume이 앱 시작 때 연결되므로, 이때 DB를 만든다 (여러 번 실행해도 안전)
        import init_db

        init_db.init_database(Config.DATABASE, verbose=False)
        app.logger.warning("DB 파일이 없어 새로 만들었습니다.")

    if app.config["TRUST_PROXY"]:
        # HTTPS 프록시가 보낸 원래 주소·https 여부를 사용 (og:url 등 전체 주소가 https로 나오도록)
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # JSON(FAQ 구조화 데이터 등)에서 한글을 그대로 보이게
    app.json.ensure_ascii = False
    # CSRF 토큰은 세션이 살아 있는 동안 유효 (작성 화면을 오래 열어 두어도 저장 가능)
    app.config["WTF_CSRF_TIME_LIMIT"] = None

    db.init_app(app)
    csrf.init_app(app)

    import auth
    import drawer
    import pages
    import reflect
    import settings

    app.register_blueprint(pages.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(drawer.bp)
    app.register_blueprint(reflect.bp)
    app.register_blueprint(settings.bp)

    app.before_request(auth.load_logged_in_user)

    @app.context_processor
    def inject_common():
        from plans import plan_status

        user = g.get("user")
        return {
            "gtm_id": app.config["GTM_CONTAINER_ID"],
            "current_user": user,
            "plan": plan_status(user) if user else None,
            # 한 번만 쓰는 표시: 다음 화면에서 꺼내 쓰고 지운다
            "ga_events": session.pop("ga_events", []),
            "clear_drafts": session.pop("clear_drafts", []),
            "C": content,
        }

    @app.errorhandler(CSRFError)
    def csrf_failed(_error):
        # 로그인이 만료되어 토큰이 맞지 않으면, 로그인 후 쓰던 화면으로 돌아가게 한다
        # (CSRF 검사는 사용자 정보를 읽기 전에 실행되므로 세션으로 판단)
        if session.get("uid") is None:
            return redirect(url_for("auth.login", next=request.path))
        return render_template("errors/500.html"), 400

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_error):
        return render_template("errors/500.html"), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
