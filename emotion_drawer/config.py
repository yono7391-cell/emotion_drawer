"""설정 값은 모두 .env 에서 읽는다. 비밀 키와 GTM 컨테이너 ID를 코드에 직접 쓰지 않는다.
GA4 측정 ID는 코드·설정 파일이 아니라 GTM 컨테이너 안에만 둔다 (PRD v4 F9)."""

import os
import re
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

_GTM_ID_PATTERN = re.compile(r"^GTM-[A-Z0-9]{4,12}$")


def _read_gtm_id() -> str:
    value = os.environ.get("GTM_CONTAINER_ID", "").strip()
    # 형식이 맞지 않는 값은 페이지에 넣지 않는다 (스크립트에 임의 문자열이 들어가는 것 방지)
    return value if _GTM_ID_PATTERN.match(value) else ""


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
    GTM_CONTAINER_ID = _read_gtm_id()
    DEBUG = os.environ.get("FLASK_DEBUG", "0").strip() == "1"

    # 로컬은 앱 폴더의 emotion_drawer.db. 배포(Railway)에서는 DATABASE_PATH로 Volume 안 경로를 지정한다
    DATABASE = Path(os.environ.get("DATABASE_PATH", "").strip() or BASE_DIR / "emotion_drawer.db")
    SCHEMA = BASE_DIR / "schema.sql"

    # 배포 환경에서만 1: HTTPS 프록시 뒤에서 https 주소를 쓰고, 로그인 쿠키를 HTTPS로만 보낸다
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "0").strip() == "1"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").strip() == "1"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # PRD F3-5 로그인 유지 7일
