"""회고 (PRD F5, F6).

- 기록 3개 미만: 안내만 보여 준다.
- 무료: 최근 30일 감정별 횟수 + 요약 문장 + 함께 기록된 감정·욕구.
- Plus: 7일 / 90일 / 전체 기간 선택. 무료 사용자가 다른 기간을 주소로 직접 요청해도 서버에서 잠금 화면.
- 문장은 횟수만 말하고 원인·사람을 단정하지 않는다 (F5-7).
"""

from datetime import timedelta

from flask import Blueprint, g, render_template, request

import content
import entries
from auth import login_required
from db import get_db, today_kst
from plans import plan_status

bp = Blueprint("reflect", __name__)

R = content.REFLECT
PERIODS = ("7", "30", "90", "all")
FREE_PERIOD = "30"
PATTERN_MIN = 2      # 같은 기록에 함께 나온 (감정, 욕구) 짝이 2번 이상일 때만
PATTERN_LIMIT = 3


def _date_from(period):
    """'최근 N일'은 오늘(한국 시간)을 포함한 N일: 오늘-(N-1)일 ~ 오늘."""
    if period == "all":
        return None
    return (today_kst() - timedelta(days=int(period) - 1)).isoformat()


def emotion_counts(conn, user_id, date_from):
    sql = """SELECT em.code, em.label, COUNT(*) AS cnt
             FROM entries e
             JOIN entry_emotions ee ON ee.entry_id = e.id
             JOIN emotions em ON em.code = ee.emotion_code
             WHERE e.user_id = ? AND e.entry_date <= ?"""
    params = [user_id, today_kst().isoformat()]
    if date_from:
        sql += " AND e.entry_date >= ?"
        params.append(date_from)
    # 횟수가 같으면 감정 목록 순서(sort_order)가 앞선 것
    sql += " GROUP BY em.code ORDER BY cnt DESC, em.sort_order"
    return [dict(r) for r in conn.execute(sql, params)]


def patterns(conn, user_id, date_from):
    sql = """SELECT em.label AS emotion, n.label AS need, COUNT(*) AS cnt
             FROM entries e
             JOIN entry_emotions ee ON ee.entry_id = e.id
             JOIN emotions em ON em.code = ee.emotion_code
             JOIN needs n ON n.code = e.need_code
             WHERE e.user_id = ? AND e.entry_date <= ?"""
    params = [user_id, today_kst().isoformat()]
    if date_from:
        sql += " AND e.entry_date >= ?"
        params.append(date_from)
    sql += """ GROUP BY ee.emotion_code, e.need_code
               HAVING COUNT(*) >= ?
               ORDER BY cnt DESC, em.sort_order, n.sort_order
               LIMIT ?"""
    params += [PATTERN_MIN, PATTERN_LIMIT]
    return [dict(r) for r in conn.execute(sql, params)]


def count_bucket(total):
    """GA4에는 기록 개수 구간만 보낸다 (F9)."""
    if total <= 5:
        return "3-5"
    if total <= 10:
        return "6-10"
    return "11+"


@bp.get("/reflect")
@login_required
def index():
    conn = get_db()
    user_id = g.user["id"]
    plan = plan_status(g.user)
    total = entries.count_for_user(conn, user_id)

    period = request.args.get("days", FREE_PERIOD)
    if period not in PERIODS:
        period = FREE_PERIOD
    locked = period != FREE_PERIOD and not plan["is_plus"]  # F6-4: 서버에서 매번 확인

    ctx = {"c": content, "R": R, "plan": plan, "total": total, "period": period,
           "periods": PERIODS, "free_period": FREE_PERIOD, "locked": locked,
           "counts": [], "summary": None, "pattern_lines": [], "bucket": None}

    if total >= 3 and not locked:
        date_from = _date_from(period)
        counts = emotion_counts(conn, user_id, date_from)
        top = max((c["cnt"] for c in counts), default=0)
        for c in counts:
            c["width"] = round(c["cnt"] / top * 100) if top else 0
        ctx["counts"] = counts
        if counts:
            ctx["summary"] = R["summary"].format(
                period=R["period_phrase"][period],
                emotion=content.with_object_particle(counts[0]["label"]),
                count=counts[0]["cnt"],
            )
        ctx["pattern_lines"] = [
            R["pattern"].format(emotion=content.with_object_particle(p["emotion"]),
                                need=content.with_object_particle(p["need"]))
            for p in patterns(conn, user_id, date_from)
        ]
        ctx["bucket"] = count_bucket(total)

    return render_template("reflect.html", **ctx)
