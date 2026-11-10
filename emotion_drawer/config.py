"""설정 값은 모두 .env 에서 읽는다. 비밀 키와 GA4 측정 ID를 코드에 직접 쓰지 않는다."""

import os
import re
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

_GA4_ID_PATTERN = re.compile(r"^G-[A-Z0-9]{4,20}$")


def _read_ga4_id() -> str:
    value = os.environ.get("GA4_MEASUREMENT_ID", "").strip()
    # 형식이 맞지 않는 값은 페이지에 넣지 않는다 (스크립트에 임의 문자열이 들어가는 것 방지)
    return value if _GA4_ID_PATTERN.match(value) else ""


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
    GA4_MEASUREMENT_ID = _read_ga4_id()
    DEBUG = os.environ.get("FLASK_DEBUG", "0").strip() == "1"

    DATABASE = BASE_DIR / "emotion_drawer.db"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # PRD F3-5 로그인 유지 7일
