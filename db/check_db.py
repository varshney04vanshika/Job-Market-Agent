import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "jobs.db"

conn = sqlite3.connect(DB_PATH)
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table'"
).fetchall()
print("Tables:", [t[0] for t in tables])
conn.close()