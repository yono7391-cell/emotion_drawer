-- 감정서랍 테이블 (PRD 5장)
-- 이미 있는 테이블은 다시 만들지 않는다.

CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    email                TEXT    NOT NULL UNIQUE,
    password_hash        TEXT    NOT NULL,
    nickname             TEXT    NOT NULL CHECK (length(nickname) BETWEEN 2 AND 12),
    marketing_consent    INTEGER NOT NULL DEFAULT 0 CHECK (marketing_consent IN (0, 1)),
    marketing_consent_at TEXT,
    plus_trial_ends_at   TEXT    NOT NULL,
    created_at           TEXT    NOT NULL,
    last_visit_at        TEXT
);

-- 감정·욕구 목록 (좋음/나쁨 같은 분류 컬럼은 두지 않는다)
CREATE TABLE IF NOT EXISTS emotions (
    code       TEXT    PRIMARY KEY,
    label      TEXT    NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS needs (
    code       TEXT    PRIMARY KEY,
    label      TEXT    NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entry_date  TEXT    NOT NULL,
    situation   TEXT    CHECK (situation IS NULL OR length(situation) <= 1000),
    thought     TEXT    CHECK (thought   IS NULL OR length(thought)   <= 1000),
    intensity   INTEGER CHECK (intensity IS NULL OR intensity BETWEEN 1 AND 5),
    need_code   TEXT    REFERENCES needs(code),
    need_note   TEXT    CHECK (need_note IS NULL OR length(need_note) <= 1000),
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entries_user_date ON entries (user_id, entry_date DESC, id DESC);

CREATE TABLE IF NOT EXISTS entry_emotions (
    entry_id     INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    emotion_code TEXT    NOT NULL REFERENCES emotions(code),
    PRIMARY KEY (entry_id, emotion_code)
);
