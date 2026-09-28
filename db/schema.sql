CREATE TABLE IF NOT EXISTS jobs_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    source_url TEXT UNIQUE,
    raw_text TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs_clean (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id INTEGER REFERENCES jobs_raw(id),
    title TEXT,
    company TEXT,
    location TEXT,
    remote_type TEXT,
    job_level TEXT,
    stipend_or_salary TEXT,
    posted_date DATE
);

CREATE TABLE IF NOT EXISTS job_skills (
    job_id INTEGER REFERENCES jobs_clean(id),
    skill TEXT
);
