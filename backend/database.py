import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "conversations.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            status TEXT NOT NULL,
            customer_name TEXT,
            transcript TEXT NOT NULL
        )
        """)
        conn.commit()

def save_conversation(call_id, status, customer_name, transcript):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO conversations VALUES (?, ?, ?, ?, ?)",
            (call_id, datetime.now().isoformat(timespec="seconds"),
             status, customer_name, transcript)
        )
        conn.commit()

def list_conversations():
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM conversations ORDER BY started_at DESC"
        ).fetchall()]
