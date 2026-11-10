"""DB 연결과 한국 시간 도우미."""

import sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import current_app, g

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)


def today_kst() -> date:
    return now_kst().date()


def now_iso() -> str:
    """DB에 저장하는 시각 형식 (한국 시간, 초 단위, 예: 2026-11-09T14:03:21+09:00)"""
    return now_kst().isoformat(timespec="seconds")


def parse_iso(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=KST)


def connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # SQLite는 연결할 때마다 외래 키를 켜야 ON DELETE CASCADE 가 동작한다
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_error=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
