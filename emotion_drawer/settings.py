"""설정: 닉네임, 이메일 소식 수신 동의, 내 기록 내려받기(CSV), 계정 삭제 (PRD F7)."""

import csv
import io

from flask import (Blueprint, Response, g, redirect, render_template, request,
                   session, url_for)

import content
from auth import login_required, queue_clear_drafts
from db import get_db, now_iso, today_kst

bp = Blueprint("settings", __name__, url_prefix="/settings")

T = content.SETTINGS
DELETE_WORD = "삭제"
# 계정을 지우면 이 기기에 남은 감정서랍 임시 보관본도 모두 지운다
ALL_DRAFT_PREFIXES = ["ed_"]


def _notice(message):
    session["settings_notice"] = message


@bp.get("")
@login_required
def index():
    return render_template(
        "settings.html", c=content, T=T,
        notice=session.pop("settings_notice", None),
        delete_error=session.pop("settings_delete_error", None),
        nickname_error=session.pop("settings_nickname_error", None),
    )


@bp.post("/nickname")
@login_required
def nickname():
    value = (request.form.get("nickname") or "").strip()
    if not 2 <= len(value) <= 12:
        session["settings_nickname_error"] = content.AUTH["nickname_rule"]
    else:
        conn = get_db()
        conn.execute("UPDATE users SET nickname = ? WHERE id = ?", (value, g.user["id"]))
        conn.commit()
        _notice(T["nickname_saved"])
    return redirect(url_for("settings.index"))


@bp.post("/consent")
@login_required
def consent():
    on = request.form.get("marketing") == "on"
    conn = get_db()
    # 동의·철회 시각을 함께 남긴다 (F7-2)
    conn.execute(
        "UPDATE users SET marketing_consent = ?, marketing_consent_at = ? WHERE id = ?",
        (int(on), now_iso(), g.user["id"]),
    )
    conn.commit()
    _notice(T["consent_on"] if on else T["consent_off"])
    return redirect(url_for("settings.index"))


def _safe_cell(value):
    """엑셀이 수식으로 실행하지 않도록 =, +, -, @ 로 시작하는 칸 앞에 ' 를 붙인다."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@bp.get("/export")
@login_required
def export():
    conn = get_db()
    rows = conn.execute(
        """SELECT e.id, e.entry_date, e.situation, e.thought, e.intensity, e.need_note,
                  e.created_at, e.updated_at, n.label AS need_label
           FROM entries e LEFT JOIN needs n ON n.code = e.need_code
           WHERE e.user_id = ?
           ORDER BY e.entry_date DESC, e.id DESC""",
        (g.user["id"],),
    ).fetchall()
    if not rows:
        _notice(T["export_empty"])
        return redirect(url_for("settings.index"))

    emotion_rows = conn.execute(
        """SELECT ee.entry_id, em.label
           FROM entry_emotions ee
           JOIN emotions em ON em.code = ee.emotion_code
           JOIN entries e ON e.id = ee.entry_id
           WHERE e.user_id = ?
           ORDER BY em.sort_order""",
        (g.user["id"],),
    )
    emotions = {}
    for r in emotion_rows:
        emotions.setdefault(r["entry_id"], []).append(r["label"])

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(T["csv_headers"])
    for r in rows:
        writer.writerow([_safe_cell(v) for v in (
            r["entry_date"], " · ".join(emotions.get(r["id"], [])), r["intensity"],
            r["situation"], r["thought"], r["need_label"], r["need_note"],
            r["created_at"], r["updated_at"],
        )])

    # UTF-8 BOM: 엑셀에서 한글이 깨지지 않도록 (F7-3)
    data = "﻿" + buf.getvalue()
    filename = f"emotion_drawer_{today_kst().strftime('%Y%m%d')}.csv"
    return Response(
        data.encode("utf-8"),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Cache-Control": "no-store"},
    )


@bp.post("/delete")
@login_required
def delete_account():
    if (request.form.get("confirm") or "").strip() != DELETE_WORD:
        session["settings_delete_error"] = T["delete_mismatch"]
        return redirect(url_for("settings.index"))

    conn = get_db()
    # 외래 키 CASCADE 로 entries·entry_emotions 도 함께 지워진다 (F7-4)
    conn.execute("DELETE FROM users WHERE id = ?", (g.user["id"],))
    conn.commit()
    session.clear()
    queue_clear_drafts(ALL_DRAFT_PREFIXES)
    return redirect(url_for("pages.landing"))
