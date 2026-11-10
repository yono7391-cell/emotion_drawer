"""Plus 체험 여부 계산 (PRD F6). 화면과 서버 모두 이 함수로 판단한다."""

import math
from datetime import timedelta

from db import now_kst, parse_iso

TRIAL_DAYS = 30  # PRD F3-3: 1개월 = 30일


def trial_end_from_now() -> str:
    return (now_kst() + timedelta(days=TRIAL_DAYS)).isoformat(timespec="seconds")


def plan_status(user) -> dict:
    """{'is_plus': bool, 'days_left': int}. 한국 시간 현재 < plus_trial_ends_at 이면 Plus."""
    if user is None:
        return {"is_plus": False, "days_left": 0}
    remaining = parse_iso(user["plus_trial_ends_at"]) - now_kst()
    seconds = remaining.total_seconds()
    if seconds <= 0:
        return {"is_plus": False, "days_left": 0}
    return {"is_plus": True, "days_left": math.ceil(seconds / 86400)}
