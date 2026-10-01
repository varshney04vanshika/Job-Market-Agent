import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Paths
DB_PATH = BASE_DIR / "db" / "jobs.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
REPORTS_DIR = BASE_DIR / "reports"
FRONTEND_DIR = BASE_DIR / "Frontend"
DATA_DIR = BASE_DIR / "data"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configurations
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen/qwen3.8-27b")

# Scraper Settings
DEFAULT_USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
)
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "15"))
