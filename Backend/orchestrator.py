import argparse
import sys
from pathlib import Path

# Safe UTF-8 console output for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from config import REPORTS_DIR, FRONTEND_DIR
from db.database import init_db, get_counts
from agents.parser_agent import JobParserAgent
from agents.market_analyst_agent import JobMarketAnalystAgent
from agents.report_generator import JobReportGenerator


def print_banner():
    banner = """
==================================================================
        JOB MARKET INTELLIGENCE & AGENTIC WEB SCRAPER             
        Autonomous Job Parsing, Skill Tagging & Reporting         
==================================================================
    """
    print(banner)


def run_pipeline(batch_size: int = 150):
    print("=" * 70)
    print(">> STARTING JOB MARKET INTELLIGENCE MISSION")
    print("=" * 70)

    # 1. Initialize DB if needed
    init_db()

    # 2. Check current status
    counts = get_counts()
    print(f"[*] Database Status: {counts['raw_jobs']:,} raw jobs | {counts['clean_jobs']:,} clean jobs | {counts['skills_tagged']:,} skills tagged")

    # 3. If clean jobs are low or unparsed jobs exist, run Parser Agent
    parser = JobParserAgent()
    if counts["clean_jobs"] < 50:
        print("\n[+] Step 1: Running Parser Agent on raw job postings...")
        parser.process_unparsed_jobs(batch_size=batch_size)
    else:
        print("\n[+] Clean job records already available in database.")
        # Process any fresh unparsed records
        parser.process_unparsed_jobs(batch_size=min(50, batch_size))

    # 4. Run Analyst Agent
    print("\n[+] Step 2: Running Market Analyst Agent...")
    analyst = JobMarketAnalystAgent()
    intelligence = analyst.generate_market_intelligence()

    # 5. Run Report Generator Agent
    print("\n[+] Step 3: Running Report Generator Agent...")
    reporter = JobReportGenerator()
    deliverables = reporter.generate_all_reports(intelligence)

    print("\n" + "=" * 70)
    print("[OK] JOB MARKET INTELLIGENCE MISSION COMPLETED!")
    print("=" * 70)
    print("Summary of Generated Deliverables:")
    print(f"  * MARKDOWN   -> {deliverables['markdown']}")
    print(f"  * HTML       -> {deliverables['html']}")
    print(f"  * FRONTEND   -> {deliverables['frontend']}")
    print(f"  * CSV DATA   -> {deliverables['csv']}")
    print("\nYou can open Frontend/index.html in your browser to view the visual dashboard!")
    return deliverables


def main():
    print_banner()

    parser = argparse.ArgumentParser(
        description="Job Market Intelligence & Agentic Web Scraper Suite"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run quick end-to-end demo (clean sample jobs, analyze, generate reports)"
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help="Run parser agent to clean and tag skills for unparsed jobs"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Number of raw job postings to parse in this batch (default: 200)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate updated Market Intelligence reports from database"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Launch the local web dashboard"
    )

    args = parser.parse_args()

    if args.demo:
        run_pipeline(batch_size=100)
    elif args.parse:
        init_db()
        p = JobParserAgent()
        p.process_unparsed_jobs(batch_size=args.limit)
    elif args.report:
        init_db()
        analyst = JobMarketAnalystAgent()
        intel = analyst.generate_market_intelligence()
        reporter = JobReportGenerator()
        reporter.generate_all_reports(intel)
    elif args.web:
        import subprocess
        print("[+] Starting Web Dashboard via app.py...")
        subprocess.run([sys.executable, "app.py"])
    else:
        # Default interactive run
        print("Executing end-to-end Job Market Intelligence pipeline...")
        run_pipeline(batch_size=args.limit)


if __name__ == "__main__":
    main()
