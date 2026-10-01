import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from config import REPORTS_DIR, FRONTEND_DIR
from db.database import get_connection


class JobReportGenerator:
    """
    Exports comprehensive Job Market Intelligence reports into
    Markdown, interactive HTML dashboards, and CSV datasets.
    """

    def __init__(self, output_dir: Path = REPORTS_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all_reports(self, intel: Dict[str, Any]) -> Dict[str, str]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = self.output_dir / f"job_market_report_{timestamp}.md"
        html_path = self.output_dir / f"job_market_report_{timestamp}.html"
        frontend_html = FRONTEND_DIR / "index.html"
        csv_path = self.output_dir / f"clean_jobs_{timestamp}.csv"

        stats = intel["statistics"]
        counts = intel["counts"]
        commentary = intel["commentary"]

        # 1. Generate Markdown Report
        self._write_markdown(md_path, counts, stats, commentary)

        # 2. Generate Interactive HTML Dashboard
        html_content = self._build_html(counts, stats, commentary)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Also copy to Frontend/index.html for live web viewing
        with open(frontend_html, "w", encoding="utf-8") as f:
            f.write(html_content)

        # 3. Export CSV of Clean Jobs
        self._export_clean_csv(csv_path)

        print(f"\n[OK] [Report Generator] Deliverables created successfully:")
        print(f"    - Markdown: {md_path.name}")
        print(f"    - HTML Report: {html_path.name}")
        print(f"    - Frontend UI: Frontend/index.html")
        print(f"    - CSV Dataset: {csv_path.name}")

        return {
            "markdown": str(md_path),
            "html": str(html_path),
            "frontend": str(frontend_html),
            "csv": str(csv_path)
        }

    def _write_markdown(self, path: Path, counts: Dict[str, int], stats: Dict[str, Any], commentary: Dict[str, Any]):
        lines = []
        lines.append("# Job Market Intelligence & Talent Demand Report")
        lines.append(f"*Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}*\n")

        lines.append("## 1. Executive Market Summary")
        lines.append(f"{commentary.get('market_summary')}\n")

        lines.append("## 2. Quantitative Database Snapshot")
        lines.append(f"- **Total Raw Postings Ingested:** `{counts.get('raw_jobs', 0):,}`")
        lines.append(f"- **Cleaned & Structured Records:** `{counts.get('clean_jobs', 0):,}`")
        lines.append(f"- **Skills Tagged Across Jobs:** `{counts.get('skills_tagged', 0):,}`\n")

        # Top Skills Table
        lines.append("## 3. Most In-Demand Skills Ranking")
        lines.append("| Rank | Skill | Job Postings | Share of Demand |")
        lines.append("|:---|:---|:---|:---|")
        top_skills = stats.get("top_skills", [])
        total_skill_mentions = sum(s["count"] for s in top_skills) or 1
        for i, s in enumerate(top_skills, 1):
            share = round((s["count"] / total_skill_mentions) * 100, 1)
            lines.append(f"| #{i} | **{s['skill']}** | {s['count']} | {share}% |")
        lines.append("")

        # Remote vs Onsite
        lines.append("## 4. Work Arrangement Distribution")
        for r in stats.get("remote_types", []):
            lines.append(f"- **{r['remote_type']}:** {r['count']} positions")
        lines.append(f"\n*{commentary.get('remote_work_index')}*\n")

        # Top Locations & Companies
        lines.append("## 5. Geographic Hotspots & Top Employers")
        lines.append("### Top Hiring Locations")
        for loc in stats.get("top_locations", [])[:7]:
            lines.append(f"- **{loc['location']}:** {loc['count']} jobs")

        lines.append("\n### Most Active Hiring Companies")
        for comp in stats.get("top_companies", [])[:7]:
            lines.append(f"- **{comp['company']}:** {comp['count']} postings")
        lines.append("")

        # Strategic Advice
        lines.append("## 6. Strategic Recommendations")
        lines.append("### For Job Seekers & Developers:")
        for rec in commentary.get("job_seeker_recommendations", []):
            lines.append(f"- {rec}")

        lines.append("\n### For Employers & Recruiters:")
        lines.append(f"- {commentary.get('employer_insights', 'Streamline hiring pipelines.')}\n")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _build_html(self, counts: Dict[str, int], stats: Dict[str, Any], commentary: Dict[str, Any]) -> str:
        skills_rows = ""
        top_skills = stats.get("top_skills", [])
        total_mentions = sum(s["count"] for s in top_skills) or 1
        for i, s in enumerate(top_skills, 1):
            pct = int((s["count"] / total_mentions) * 100)
            skills_rows += f"""
            <tr>
                <td style="font-weight: 600;">#{i}</td>
                <td><span class="badge badge-blue">{s['skill']}</span></td>
                <td><strong>{s['count']}</strong></td>
                <td>
                    <div style="background: #e2e8f0; border-radius: 4px; height: 10px; width: 100%;">
                        <div style="background: #3b82f6; width: {pct * 3}%; max-width: 100%; height: 100%; border-radius: 4px;"></div>
                    </div>
                </td>
            </tr>
            """

        recs_html = "".join([f"<li>{r}</li>" for r in commentary.get("job_seeker_recommendations", [])])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Job Market Intelligence Dashboard</title>
    <style>
        :root {{
            --primary: #2563eb;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #0f172a;
            --muted: #64748b;
            --border: #e2e8f0;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            padding: 2rem 1rem;
            line-height: 1.6;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}
        header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            color: white;
            padding: 2.2rem;
            border-radius: 1rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
        }}
        header h1 {{ font-size: 2rem; margin-bottom: 0.4rem; }}
        header p {{ color: #bfdbfe; font-size: 0.95rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: var(--card);
            border: 1px solid var(--border);
            padding: 1.25rem;
            border-radius: 0.75rem;
            text-align: center;
        }}
        .stat-card .val {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
        .stat-card .lbl {{ font-size: 0.85rem; color: var(--muted); text-transform: uppercase; margin-top: 0.25rem; }}
        .card {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            padding: 1.75rem;
            margin-bottom: 2rem;
        }}
        .card h2 {{
            font-size: 1.3rem;
            color: #1e293b;
            margin-bottom: 1rem;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 0.5rem;
        }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1rem; }}
        th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border); font-size: 0.92rem; }}
        th {{ background: #f8fafc; color: #475569; font-weight: 600; }}
        .badge {{ padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.78rem; font-weight: 600; }}
        .badge-blue {{ background: #dbeafe; color: #1d4ed8; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
        @media(max-width: 768px) {{ .two-col {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Job Market Intelligence & Talent Demand</h1>
            <p>Autonomous AI Labor Market Analytics &bull; Updated on {datetime.now().strftime('%B %d, %Y')}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="val">{counts.get('raw_jobs', 0):,}</div>
                <div class="lbl">Raw Jobs Scraped</div>
            </div>
            <div class="stat-card">
                <div class="val">{counts.get('clean_jobs', 0):,}</div>
                <div class="lbl">Clean Normalized Jobs</div>
            </div>
            <div class="stat-card">
                <div class="val">{counts.get('skills_tagged', 0):,}</div>
                <div class="lbl">Skills Tagged</div>
            </div>
        </div>

        <section class="card">
            <h2>Executive Market Dynamics</h2>
            <p style="font-size: 1.05rem; color: #334155; margin-bottom: 1rem;">{commentary.get('market_summary')}</p>
            <p style="color: #475569;"><strong>Tech Skill Trends:</strong> {commentary.get('skill_demand_trends')}</p>
            <p style="color: #475569; margin-top: 0.5rem;"><strong>Workplace Modality:</strong> {commentary.get('remote_work_index')}</p>
        </section>

        <section class="card">
            <h2>Top 15 Most Demanded Skills</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 10%;">Rank</th>
                        <th style="width: 30%;">Skill / Technology</th>
                        <th style="width: 25%;">Mentions</th>
                        <th style="width: 35%;">Relative Demand</th>
                    </tr>
                </thead>
                <tbody>
                    {skills_rows}
                </tbody>
            </table>
        </section>

        <div class="two-col">
            <section class="card">
                <h2>Top Hiring Locations</h2>
                <ul>
                    {"".join([f"<li style='margin-bottom: 0.5rem;'><strong>{loc['location']}</strong>: {loc['count']} postings</li>" for loc in stats.get('top_locations', [])[:6]])}
                </ul>
            </section>
            <section class="card">
                <h2>Most Active Employers</h2>
                <ul>
                    {"".join([f"<li style='margin-bottom: 0.5rem;'><strong>{comp['company']}</strong>: {comp['count']} roles</li>" for comp in stats.get('top_companies', [])[:6]])}
                </ul>
            </section>
        </div>

        <section class="card">
            <h2>Strategic Career & Hiring Recommendations</h2>
            <h3 style="font-size: 1rem; color: var(--primary); margin-bottom: 0.5rem;">For Candidates:</h3>
            <ul style="padding-left: 1.5rem; margin-bottom: 1rem;">
                {recs_html}
            </ul>
            <h3 style="font-size: 1rem; color: var(--primary); margin-bottom: 0.5rem;">For Employers:</h3>
            <p style="color: #334155;">{commentary.get('employer_insights')}</p>
        </section>
    </div>
</body>
</html>
"""

    def _export_clean_csv(self, path: Path):
        conn = get_connection()
        query = """
            SELECT c.id, c.title, c.company, c.location, c.remote_type, c.job_level, c.stipend_or_salary,
                   GROUP_CONCAT(s.skill, ', ') as skills
            FROM jobs_clean c
            LEFT JOIN job_skills s ON c.id = s.job_id
            GROUP BY c.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        df.to_csv(path, index=False, encoding="utf-8")
