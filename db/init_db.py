import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "jobs.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()
    print("Database created at", DB_PATH)

if __name__ == "__main__":
    init_db()
