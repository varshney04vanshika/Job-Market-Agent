import sqlite3
import time
import requests
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db" / "jobs.db"

ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def get_current_thread_id():
    """Find the latest 'Who is hiring?' thread automatically."""
    params = {"query": "Who is hiring", "tags": "story", "hitsPerPage": 1}
    resp = requests.get(ALGOLIA_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    if not hits:
        raise RuntimeError("Could not find a 'Who is hiring' thread.")
    return int(hits[0]["objectID"])


def fetch_item(item_id):
    resp = requests.get(HN_ITEM_URL.format(item_id), timeout=10)
    resp.raise_for_status()
    return resp.json()


def scrape_and_save(thread_id=None, delay=0.3):
    if thread_id is None:
        thread_id = get_current_thread_id()
        print(f"Using latest thread: {thread_id}")

    thread = fetch_item(thread_id)
    comment_ids = thread.get("kids", [])
    print(f"Found {len(comment_ids)} postings in thread {thread_id}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    inserted, skipped, empty = 0, 0, 0
    for i, comment_id in enumerate(comment_ids, start=1):
        comment = fetch_item(comment_id)
        text = comment.get("text")

        if not text:
            empty += 1
            continue

        source_url = f"https://news.ycombinator.com/item?id={comment_id}"

        try:
            cursor.execute(
                """
                INSERT INTO jobs_raw (source, source_url, raw_text)
                VALUES (?, ?, ?)
                """,
                ("hackernews", source_url, text),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

        if i % 20 == 0:
            print(f"Processed {i}/{len(comment_ids)}...")

        time.sleep(delay)  # be polite to the free API

    conn.commit()
    conn.close()
    print(f"Done. Inserted: {inserted}, Skipped (duplicates): {skipped}, Empty/deleted: {empty}")


if __name__ == "__main__":
    scrape_and_save()
