import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent.parent / "db" / "jobs.db"
CSV_PATH = Path(__file__).parent.parent / "data" / "raw" / "internshala.csv"

def load_csv_to_raw():
    df = pd.read_csv(CSV_PATH)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted, skipped = 0, 0
    for _, row in df.iterrows():
        raw_text = (
            f"Title: {row['Title']} | "
            f"Company: {row['Company Name']} | "
            f"Location: {row['Location']} | "
            f"Start Date: {row['Start Date']} | "
            f"Duration: {row['Duration']} | "
            f"Stipend: {row['Stipend']} | "
            f"Status: {row['Status']}"
        )
        source_url = row["Links"]

        try:
            cursor.execute(
                """
                INSERT INTO jobs_raw (source, source_url, raw_text)
                VALUES (?, ?, ?)
                """,
                ("internshala_dataset", source_url, raw_text),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Inserted: {inserted}, Skipped (duplicates): {skipped}")

if __name__ == "__main__":
    load_csv_to_raw()