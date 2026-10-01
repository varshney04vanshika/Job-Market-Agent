# 💼 Job Market Intelligence & Agentic Web Scraper Suite

An end-to-end multi-agent AI system for scraping, parsing, skill-tagging, and synthesizing labor market intelligence from tech job postings and internship datasets.

---

## 🏛️ System Architecture

```
[ Raw Postings: Internshala / Hacker News ]
                    │
                    ▼
  1. 🕷️ Scrapers (scrapers/) ───────► Stores raw unparsed postings into SQLite `jobs_raw`
                    │
                    ▼
  2. 🧠 Parser Agent (agents/parser_agent.py)
     └── Normalizes locations, job level, salary/stipends, and extracts tech skills into `jobs_clean` & `job_skills`
                    │
                    ▼
  3. 📊 Market Analyst Agent (agents/market_analyst_agent.py)
     └── Aggregates skill demand rankings, remote work index, location hotspots, and hiring trends
                    │
                    ▼
  4. 📝 Report Generator (agents/report_generator.py)
     └── Outputs Markdown reports, interactive HTML dashboard, and clean CSV datasets
                    │
                    ▼
  5. 🌐 Web Dashboard (app.py) ─────► Live local dashboard on http://127.0.0.1:5000
```

---

## 🚀 How to Run in VS Code

### 1. Instant Demo
Runs the end-to-end pipeline (cleans a batch of jobs, runs market analysis, and generates reports):
```powershell
python main.py --demo
```

### 2. Parse Raw Jobs in Batches
Clean and tag skills for unparsed raw job postings:
```powershell
python main.py --parse --limit 200
```

### 3. Generate Fresh Market Intelligence Reports
```powershell
python main.py --report
```

### 4. Launch the Interactive Web Dashboard
```powershell
python app.py
```
Open **http://127.0.0.1:5000** in your web browser.

---

## 📁 Output Deliverables

All generated outputs are stored in:
- `reports/job_market_report_<timestamp>.md` — Executive Markdown summary
- `reports/job_market_report_<timestamp>.html` — Interactive visual dashboard
- `Frontend/index.html` — Updated live web UI
- `reports/clean_jobs_<timestamp>.csv` — Clean normalized CSV dataset with skills
