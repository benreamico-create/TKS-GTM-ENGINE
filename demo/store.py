import json
import sqlite3
from pathlib import Path


class SignalStore:
    def __init__(self, db_path: str = "data/signals.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init()

    def _init(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id TEXT PRIMARY KEY,
                source TEXT,
                name TEXT,
                github_url TEXT,
                project_name TEXT,
                project_url TEXT,
                project_description TEXT,
                competition TEXT,
                location TEXT,
                relevance_score REAL,
                score_reason TEXT,
                email_draft TEXT,
                detected_at TEXT DEFAULT (datetime('now')),
                raw_data TEXT
            )
        """)
        self.conn.commit()

    def exists(self, signal_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM signals WHERE id=?", (signal_id,)
        ).fetchone() is not None

    def save(self, signal: dict) -> bool:
        try:
            self.conn.execute(
                """INSERT INTO signals
                   (id, source, name, github_url, project_name, project_url,
                    project_description, competition, location, relevance_score,
                    score_reason, raw_data)
                   VALUES (:id,:source,:name,:github_url,:project_name,:project_url,
                    :project_description,:competition,:location,:relevance_score,
                    :score_reason,:raw_data)""",
                {**signal, "raw_data": json.dumps(signal.get("raw_data", {}))},
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def save_email_draft(self, signal_id: str, draft: str):
        self.conn.execute(
            "UPDATE signals SET email_draft=? WHERE id=?", (draft, signal_id)
        )
        self.conn.commit()

    def get_all(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM signals ORDER BY relevance_score DESC, detected_at DESC"
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_by_id(self, signal_id: str) -> dict | None:
        cur = self.conn.execute("SELECT * FROM signals WHERE id=?", (signal_id,))
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        return dict(zip(cols, row)) if row else None

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
