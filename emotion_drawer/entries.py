"""기록 한 건의 입력값 검사와 저장 (PRD F2, F4, 5장).

작성(/drawer/new)·수정(/drawer/<id>/edit)·체험 보관(/drawer/import-try)이 모두 이 검사를 거친다.
조회·수정·삭제는 항상 user_id 조건을 함께 건다 (다른 사람 기록 접근 차단).
"""

from datetime import date

import content
from db import now_iso, today_kst

MAX_TEXT = 1000
MAX_EMOTIONS = 3
TEXT_FIELDS = ("situation", "thought", "need_note")
WEEKDAYS = "월화수목금토일"


class EntryError(ValueError):
    """화면에 그대로 보여 줄 안내 문구를 담는다."""


def _clean_text(value):
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").strip()
    if len(text) > MAX_TEXT:
        raise EntryError(content.MESSAGES["text_max"])
    return text or None


def validate(conn, raw: dict, allow_date=True) -> dict:
    """raw: {'situation','thought','emotions'(list),'intensity','need_code','need_note','entry_date'}"""
    cleaned = {f: _clean_text(raw.get(f)) for f in TEXT_FIELDS}

    emotions = []
    for code in raw.get("emotions") or []:
        code = str(code)
        if code not in emotions:
            emotions.append(code)
    if not emotions:
        raise EntryError(content.MESSAGES["emotion_required"])
    if len(emotions) > MAX_EMOTIONS:
        raise EntryError(content.MESSAGES["emotion_max"])
    placeholders = ",".join("?" * len(emotions))
    known = {r["code"] for r in conn.execute(
        f"SELECT code FROM emotions WHERE code IN ({placeholders})", emotions)}
    if len(known) != len(emotions):
        raise EntryError(content.MESSAGES["emotion_required"])
    cleaned["emotions"] = emotions

    intensity = raw.get("intensity")
    if intensity in (None, ""):
        cleaned["intensity"] = None
    else:
        try:
            intensity = int(intensity)
        except (TypeError, ValueError):
            intensity = None
        cleaned["intensity"] = intensity if intensity in range(1, 6) else None

    need = raw.get("need_code") or None
    if need is not None and not conn.execute("SELECT 1 FROM needs WHERE code = ?", (str(need),)).fetchone():
        need = None
    cleaned["need_code"] = need

    today = today_kst()
    entry_date = today
    if allow_date and raw.get("entry_date"):
        try:
            picked = date.fromisoformat(str(raw["entry_date"]))
            if picked <= today:  # 앞으로의 날짜는 받지 않는다
                entry_date = picked
        except ValueError:
            pass
    cleaned["entry_date"] = entry_date.isoformat()
    return cleaned


def from_form(form) -> dict:
    return {
        "situation": form.get("situation"),
        "thought": form.get("thought"),
        "emotions": form.getlist("emotions"),
        "intensity": form.get("intensity"),
        "need_code": form.get("need_code"),
        "need_note": form.get("need_note"),
        "entry_date": form.get("entry_date"),
    }


def from_try_json(data: dict) -> dict:
    """브라우저에 임시 보관된 체험 기록(write.js 형식)을 저장 형식으로."""
    data = data if isinstance(data, dict) else {}
    emotions = data.get("emotions")
    return {
        "situation": data.get("situation"),
        "thought": data.get("thought"),
        "emotions": emotions if isinstance(emotions, list) else [],
        "intensity": data.get("intensity"),
        "need_code": data.get("needCode"),
        "need_note": data.get("needNote"),
        "entry_date": None,
    }


def _write_emotions(conn, entry_id, emotions):
    conn.execute("DELETE FROM entry_emotions WHERE entry_id = ?", (entry_id,))
    conn.executemany(
        "INSERT INTO entry_emotions (entry_id, emotion_code) VALUES (?, ?)",
        [(entry_id, code) for code in emotions],
    )


def create(conn, user_id, cleaned) -> tuple[int, bool]:
    """저장하고 (기록 id, 첫 기록인지)를 돌려준다."""
    is_first = conn.execute("SELECT 1 FROM entries WHERE user_id = ? LIMIT 1", (user_id,)).fetchone() is None
    now = now_iso()
    cur = conn.execute(
        """INSERT INTO entries (user_id, entry_date, situation, thought, intensity,
               need_code, need_note, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, cleaned["entry_date"], cleaned["situation"], cleaned["thought"],
         cleaned["intensity"], cleaned["need_code"], cleaned["need_note"], now, now),
    )
    _write_emotions(conn, cur.lastrowid, cleaned["emotions"])
    conn.commit()
    return cur.lastrowid, is_first


def update(conn, user_id, entry_id, cleaned) -> bool:
    cur = conn.execute(
        """UPDATE entries SET entry_date = ?, situation = ?, thought = ?, intensity = ?,
               need_code = ?, need_note = ?, updated_at = ?
           WHERE id = ? AND user_id = ?""",
        (cleaned["entry_date"], cleaned["situation"], cleaned["thought"], cleaned["intensity"],
         cleaned["need_code"], cleaned["need_note"], now_iso(), entry_id, user_id),
    )
    if cur.rowcount != 1:
        conn.rollback()
        return False
    _write_emotions(conn, entry_id, cleaned["emotions"])
    conn.commit()
    return True


def delete(conn, user_id, entry_id) -> bool:
    cur = conn.execute("DELETE FROM entries WHERE id = ? AND user_id = ?", (entry_id, user_id))
    conn.commit()
    return cur.rowcount == 1


def _emotions_by_entry(conn, entry_ids):
    result = {i: [] for i in entry_ids}
    if not entry_ids:
        return result
    placeholders = ",".join("?" * len(entry_ids))
    rows = conn.execute(
        f"""SELECT ee.entry_id, em.code, em.label
            FROM entry_emotions ee JOIN emotions em ON em.code = ee.emotion_code
            WHERE ee.entry_id IN ({placeholders})
            ORDER BY em.sort_order""",
        list(entry_ids),
    )
    for r in rows:
        result[r["entry_id"]].append({"code": r["code"], "label": r["label"]})
    return result


def get(conn, user_id, entry_id):
    """내 기록 한 건 (없거나 다른 사람 기록이면 None)."""
    row = conn.execute(
        """SELECT e.*, n.label AS need_label
           FROM entries e LEFT JOIN needs n ON n.code = e.need_code
           WHERE e.id = ? AND e.user_id = ?""",
        (entry_id, user_id),
    ).fetchone()
    if row is None:
        return None
    entry = dict(row)
    entry["emotions"] = _emotions_by_entry(conn, [entry_id])[entry_id]
    return entry


def list_for_user(conn, user_id, emotion=None, keyword=None, limit=20):
    """최신순 목록. (기록들, 더 있는지) 를 돌려준다."""
    sql = ["SELECT e.* FROM entries e WHERE e.user_id = ?"]
    params = [user_id]
    if emotion:
        sql.append("AND e.id IN (SELECT entry_id FROM entry_emotions WHERE emotion_code = ?)")
        params.append(emotion)
    if keyword:
        sql.append("AND (instr(coalesce(e.situation, ''), ?) > 0"
                   " OR instr(coalesce(e.thought, ''), ?) > 0"
                   " OR instr(coalesce(e.need_note, ''), ?) > 0)")
        params += [keyword, keyword, keyword]
    sql.append("ORDER BY e.entry_date DESC, e.id DESC LIMIT ?")
    params.append(limit + 1)
    rows = [dict(r) for r in conn.execute(" ".join(sql), params)]
    has_more = len(rows) > limit
    rows = rows[:limit]
    emotions = _emotions_by_entry(conn, [r["id"] for r in rows])
    for r in rows:
        r["emotions"] = emotions[r["id"]]
    return rows, has_more


def count_for_user(conn, user_id) -> int:
    return conn.execute("SELECT COUNT(*) FROM entries WHERE user_id = ?", (user_id,)).fetchone()[0]


def short_date(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{d.month:02d}.{d.day:02d} ({WEEKDAYS[d.weekday()]})"


def long_date(iso_date: str) -> str:
    d = date.fromisoformat(iso_date)
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def first_line(text, limit=40) -> str:
    if not text:
        return ""
    line = text.strip().splitlines()[0]
    return line if len(line) <= limit else line[:limit] + "…"
