import json
import sqlite3
from pathlib import Path

from models import StudentSignal


class SignalStore:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                external_id TEXT NOT NULL,
                name TEXT,
                email TEXT,
                github_url TEXT,
                project_name TEXT,
                competition TEXT,
                relevance_score REAL,
                score_reason TEXT,
                detected_at TEXT,
                raw_data TEXT,
                UNIQUE(source, external_id)
            )
        """)
        self.conn.commit()

    def is_seen(self, source: str, external_id: str) -> bool:
        cur = self.conn.execute(
            "SELECT 1 FROM signals WHERE source=? AND external_id=?",
            (source, external_id),
        )
        return cur.fetchone() is not None

    def save(self, signal: StudentSignal) -> bool:
        """Returns True if new, False if duplicate."""
        try:
            self.conn.execute(
                """INSERT INTO signals
                   (id, source, external_id, name, email, github_url,
                    project_name, competition, relevance_score, score_reason,
                    detected_at, raw_data)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    signal.id,
                    signal.source,
                    signal.external_id,
                    signal.name,
                    signal.email,
                    signal.github_url,
                    signal.project_name,
                    signal.competition,
                    signal.relevance_score,
                    signal.score_reason,
                    signal.detected_at.isoformat(),
                    json.dumps(signal.raw_data),
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_recent(self, limit: int = 100) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM signals ORDER BY detected_at DESC LIMIT ?", (limit,)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
