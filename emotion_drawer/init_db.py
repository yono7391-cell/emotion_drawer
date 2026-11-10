"""DB 파일과 테이블을 만들고 감정·욕구 목록을 채운다.

여러 번 실행해도 안전하다: 테이블은 없을 때만 만들고, 목록은 없는 항목만 추가한다.
사용자·기록 데이터는 건드리지 않는다.
"""

from pathlib import Path

from config import Config
from db import connect

# (code, label) — PRD 5-3. 앱은 이 목록을 코드가 아닌 DB에서 읽는다.
EMOTIONS = [
    ("joy", "기쁨"),
    ("calm", "편안함"),
    ("gratitude", "감사"),
    ("excitement", "설렘"),
    ("pride", "뿌듯함"),
    ("sadness", "슬픔"),
    ("anxiety", "불안"),
    ("anger", "화남"),
    ("hurt", "서운함"),
    ("loneliness", "외로움"),
    ("exhaustion", "지침"),
    ("confusion", "혼란"),
]

NEEDS = [
    ("rest", "휴식"),
    ("recognition", "인정"),
    ("understanding", "이해받음"),
    ("connection", "연결"),
    ("safety", "안전"),
    ("autonomy", "자율"),
    ("achievement", "성취"),
    ("enjoyment", "즐거움"),
]


def main() -> None:
    init_database()


def init_database(path=None, verbose: bool = True) -> None:
    """path 를 주지 않으면 설정의 DB 경로(Config.DATABASE)를 쓴다. 앱 시작 시 DB가 없을 때도 호출된다."""
    path = Path(path or Config.DATABASE)
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = Config.SCHEMA.read_text(encoding="utf-8")
    conn = connect(path)
    try:
        conn.executescript(schema)
        conn.executemany(
            "INSERT OR IGNORE INTO emotions (code, label, sort_order) VALUES (?, ?, ?)",
            [(code, label, i) for i, (code, label) in enumerate(EMOTIONS, start=1)],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO needs (code, label, sort_order) VALUES (?, ?, ?)",
            [(code, label, i) for i, (code, label) in enumerate(NEEDS, start=1)],
        )
        conn.commit()
        if not verbose:
            return

        tables = [r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )]
        print(f"DB: {path.name}")
        for name in tables:
            count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            print(f"  {name}: {count}행")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
