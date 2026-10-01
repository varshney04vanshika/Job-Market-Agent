import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
from flask import Flask, jsonify, request, send_file
from config.settings import DB_PATH, FRONTEND_DIR, REPORTS_DIR
from db.database import get_counts, get_market_statistics, get_connection
from agents.parser_agent import JobParserAgent
from agents.market_analyst_agent import JobMarketAnalystAgent
from agents.report_generator import JobReportGenerator
from agents.qa_agent import JobMarketQAAgent

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


@app.route("/")
def index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()

    # Generate if not exists
    analyst = JobMarketAnalystAgent()
    intel = analyst.generate_market_intelligence()
    reporter = JobReportGenerator()
    reporter.generate_all_reports(intel)
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/api/stats")
def api_stats():
    counts = get_counts()
    stats = get_market_statistics()
    return jsonify({
        "counts": counts,
        "statistics": stats
    })


@app.route("/api/chart-data")
def api_chart_data():
    """Returns Chart.js formatted payloads for direct frontend rendering."""
    stats = get_market_statistics()

    # Top skills
    skills_labels = [s["skill"] for s in stats.get("top_skills", [])[:10]]
    skills_values = [s["count"] for s in stats.get("top_skills", [])[:10]]

    # Remote types
    remote_labels = [r["remote_type"] for r in stats.get("remote_types", [])]
    remote_values = [r["count"] for r in stats.get("remote_types", [])]

    # Locations
    loc_labels = [l["location"] for l in stats.get("top_locations", [])[:8]]
    loc_values = [l["count"] for l in stats.get("top_locations", [])[:8]]

    # Companies
    comp_labels = [c["company"][:20] for c in stats.get("top_companies", [])[:8]]
    comp_values = [c["count"] for c in stats.get("top_companies", [])[:8]]

    return jsonify({
        "skills": {"labels": skills_labels, "data": skills_values},
        "remote": {"labels": remote_labels, "data": remote_values},
        "locations": {"labels": loc_labels, "data": loc_values},
        "companies": {"labels": comp_labels, "data": comp_values}
    })


@app.route("/api/jobs")
def api_jobs():
    limit = int(request.args.get("limit", 60))
    skill_filter = request.args.get("skill", "").strip()
    remote_filter = request.args.get("remote", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_connection()
    conditions = []
    params = []

    if skill_filter:
        conditions.append("s.skill LIKE ?")
        params.append(f"%{skill_filter}%")
    if remote_filter:
        conditions.append("c.remote_type = ?")
        params.append(remote_filter)
    if search:
        conditions.append("(c.title LIKE ? OR c.company LIKE ? OR c.location LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
        SELECT c.id, c.title, c.company, c.location, c.remote_type, c.job_level, c.stipend_or_salary,
               GROUP_CONCAT(DISTINCT s.skill) as skills
        FROM jobs_clean c
        LEFT JOIN job_skills s ON c.id = s.job_id
        {where_clause}
        GROUP BY c.id
        ORDER BY c.id DESC
        LIMIT ?
    """
    params.append(limit)

    rows = conn.execute(query, tuple(params)).fetchall()
    conn.close()

    return jsonify([dict(r) for r in rows])


@app.route("/api/ask", methods=["GET", "POST"])
def api_ask():
    """Natural Language Q&A assistant powered by JobMarketQAAgent."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        question = data.get("question", "")
    else:
        question = request.args.get("q", "")

    if not question:
        return jsonify({"error": "No question provided"}), 400

    qa = JobMarketQAAgent()
    result = qa.answer_question(question)
    return jsonify(result)


@app.route("/api/process", methods=["POST"])
def api_process():
    batch = int(request.args.get("batch", 150))
    parser = JobParserAgent()
    processed = parser.process_unparsed_jobs(batch_size=batch)

    analyst = JobMarketAnalystAgent()
    intel = analyst.generate_market_intelligence()
    reporter = JobReportGenerator()
    reporter.generate_all_reports(intel)

    return jsonify({
        "success": True,
        "processed_count": processed,
        "new_counts": get_counts()
    })


if __name__ == "__main__":
    print("[+] Launching Job Market Intelligence Web App on http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
