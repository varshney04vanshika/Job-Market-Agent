import sqlite3
from typing import List, Dict, Any, Tuple
from config import DB_PATH, SCHEMA_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def get_counts() -> Dict[str, int]:
    conn = get_connection()
    c = conn.cursor()
    raw_count = c.execute("SELECT COUNT(*) FROM jobs_raw").fetchone()[0]
    clean_count = c.execute("SELECT COUNT(*) FROM jobs_clean").fetchone()[0]
    skills_count = c.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0]
    conn.close()
    return {
        "raw_jobs": raw_count,
        "clean_jobs": clean_count,
        "skills_tagged": skills_count
    }


def get_unparsed_raw_jobs(limit: int = 100) -> List[sqlite3.Row]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT r.id, r.source, r.source_url, r.raw_text
        FROM jobs_raw r
        LEFT JOIN jobs_clean c ON r.id = c.raw_id
        WHERE c.id IS NULL
        LIMIT ?
    """
    rows = cursor.execute(query, (limit,)).fetchall()
    conn.close()
    return rows


def insert_clean_job_record(
    raw_id: int,
    title: str,
    company: str,
    location: str,
    remote_type: str,
    job_level: str,
    stipend_or_salary: str,
    posted_date: str,
    skills: List[str]
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO jobs_clean (raw_id, title, company, location, remote_type, job_level, stipend_or_salary, posted_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (raw_id, title, company, location, remote_type, job_level, stipend_or_salary, posted_date)
    )
    clean_id = cursor.lastrowid

    for skill in set(skills):
        skill_clean = skill.strip()
        if skill_clean:
            cursor.execute(
                "INSERT INTO job_skills (job_id, skill) VALUES (?, ?)",
                (clean_id, skill_clean)
            )

    conn.commit()
    conn.close()
    return clean_id


def get_market_statistics() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    # Top skills
    top_skills = cursor.execute(
        """
        SELECT skill, COUNT(*) as count 
        FROM job_skills 
        GROUP BY skill 
        ORDER BY count DESC 
        LIMIT 15
        """
    ).fetchall()

    # Remote breakdown
    remote_types = cursor.execute(
        """
        SELECT remote_type, COUNT(*) as count 
        FROM jobs_clean 
        GROUP BY remote_type 
        ORDER BY count DESC
        """
    ).fetchall()

    # Top locations
    top_locations = cursor.execute(
        """
        SELECT location, COUNT(*) as count 
        FROM jobs_clean 
        WHERE location != 'Unspecified' AND location != '' 
        GROUP BY location 
        ORDER BY count DESC 
        LIMIT 10
        """
    ).fetchall()

    # Top hiring companies
    top_companies = cursor.execute(
        """
        SELECT company, COUNT(*) as count 
        FROM jobs_clean 
        WHERE company != 'Confidential' AND company != 'Unknown' AND company != '' 
        GROUP BY company 
        ORDER BY count DESC 
        LIMIT 10
        """
    ).fetchall()

    # Job levels
    job_levels = cursor.execute(
        """
        SELECT job_level, COUNT(*) as count 
        FROM jobs_clean 
        GROUP BY job_level 
        ORDER BY count DESC
        """
    ).fetchall()

    conn.close()

    return {
        "top_skills": [dict(r) for r in top_skills],
        "remote_types": [dict(r) for r in remote_types],
        "top_locations": [dict(r) for r in top_locations],
        "top_companies": [dict(r) for r in top_companies],
        "job_levels": [dict(r) for r in job_levels]
    }
