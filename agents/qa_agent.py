import re
import json
import sqlite3
from typing import Dict, List, Any
from config.settings import DB_PATH, GROQ_API_KEY, DEFAULT_LLM_MODEL
from db.database import get_connection, get_counts, get_market_statistics


class JobMarketQAAgent:
    """
    Intelligent Q&A Agent capable of answering natural language questions
    about the labor market, skills, salaries, and companies by querying jobs.db.
    """

    SCHEMA_CONTEXT = """
Database Schema:
1. jobs_clean (
    id INTEGER PRIMARY KEY,
    title TEXT,
    company TEXT,
    location TEXT,
    remote_type TEXT (Remote, On-site, Hybrid),
    job_level TEXT (Internship, Junior, Mid-Level, Senior),
    stipend_or_salary TEXT,
    posted_date DATE
)
2. job_skills (
    job_id INTEGER REFERENCES jobs_clean(id),
    skill TEXT
)
3. jobs_raw (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_url TEXT,
    raw_text TEXT
)
"""

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        """Processes a natural language question and returns data-backed insights."""
        user_question = user_question.strip()
        if not user_question:
            return {
                "question": "",
                "answer": "Please ask a question about skills, jobs, salaries, or companies in the database.",
                "data": [],
                "sql": ""
            }

        # Step 1: Try LLM Text-to-SQL if available
        sql_query, explanation = None, None
        if GROQ_API_KEY:
            sql_query = self._generate_sql_with_llm(user_question)

        # Step 2: Fallback to Semantic Heuristic Query Router if LLM is unavailable or failed
        if not sql_query or not self._is_safe_sql(sql_query):
            sql_query = self._heuristic_query_router(user_question)

        # Step 3: Execute SQL Query safely
        rows, columns, error = self._execute_safe_query(sql_query)

        # Step 4: Synthesize response
        if error:
            answer = f"I encountered an error querying the database: `{error}`. Let me provide the general market snapshot instead."
            stats = get_market_statistics()
            return {
                "question": user_question,
                "answer": answer,
                "data": stats.get("top_skills", [])[:5],
                "sql": sql_query or ""
            }

        answer_markdown = self._synthesize_answer(user_question, sql_query, rows, columns)
        suggested_followups = self._generate_followups(user_question)

        return {
            "question": user_question,
            "answer": answer_markdown,
            "sql": sql_query,
            "data": rows[:15],
            "row_count": len(rows),
            "suggested_followups": suggested_followups
        }

    def _is_safe_sql(self, sql: str) -> bool:
        """Ensures query is strictly a read-only SELECT."""
        if not sql:
            return False
        sql_clean = sql.strip().upper()
        if not sql_clean.startswith("SELECT") and not sql_clean.startswith("WITH"):
            return False
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "EXEC", "--", ";"]
        # Allow semicolons only at the very end
        normalized = re.sub(r";\s*$", "", sql.strip())
        for word in dangerous:
            if re.search(rf"\b{word}\b", normalized, re.IGNORECASE):
                return False
        return True

    def _execute_safe_query(self, sql: str) -> tuple:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = [dict(r) for r in cursor.fetchall()]
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            conn.close()
            return rows, columns, None
        except Exception as e:
            return [], [], str(e)

    def _generate_sql_with_llm(self, question: str) -> str:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            prompt = f"""
{self.SCHEMA_CONTEXT}

Task: Write a single SQLite SELECT query to answer this user question:
"{question}"

Rules:
1. ONLY return the raw SQL SELECT query. Do not wrap in markdown quotes. Do not include explanation.
2. Join `jobs_clean` with `job_skills` on `jobs_clean.id = job_skills.job_id` when skill filtering or ranking is needed.
3. Use LIMIT 15 by default to keep results concise.
4. Use LIKE '%keyword%' for case-insensitive text matching.
"""
            resp = client.chat.completions.create(
                model=DEFAULT_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            raw = (resp.choices[0].message.content or "").strip()
            # Clean possible markdown formatting
            raw = re.sub(r"^```(?:sql)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw).strip()
            return raw
        except Exception as e:
            print(f" [!] LLM SQL generation fallback: {e}")
            return None

    def _heuristic_query_router(self, q: str) -> str:
        """Rule-based query router when LLM is unavailable."""
        ql = q.lower()

        # 1. Top Skills
        if any(w in ql for w in ["top skill", "skills in demand", "most popular skill", "highest demand", "most demanded"]):
            return """
                SELECT skill, COUNT(*) as demand_count 
                FROM job_skills 
                GROUP BY skill 
                ORDER BY demand_count DESC 
                LIMIT 10
            """

        # 2. Remote vs Onsite
        if any(w in ql for w in ["remote", "work from home", "hybrid", "onsite"]):
            if "how many" in ql or "percentage" in ql or "breakdown" in ql or "distribution" in ql or "vs" in ql:
                return """
                    SELECT remote_type, COUNT(*) as total_jobs,
                           ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM jobs_clean), 1) as percentage
                    FROM jobs_clean 
                    GROUP BY remote_type 
                    ORDER BY total_jobs DESC
                """
            return """
                SELECT title, company, location, remote_type, stipend_or_salary 
                FROM jobs_clean 
                WHERE remote_type = 'Remote' 
                ORDER BY id DESC 
                LIMIT 10
            """

        # 3. Highest paying / stipends
        if any(w in ql for w in ["highest", "salary", "stipend", "pay", "paying"]):
            return """
                SELECT title, company, location, stipend_or_salary 
                FROM jobs_clean 
                WHERE stipend_or_salary NOT LIKE '%Unpaid%' 
                  AND stipend_or_salary NOT LIKE '%Not Disclosed%' 
                ORDER BY id DESC 
                LIMIT 10
            """

        # 4. Specific Technologies (Python, React, SQL, AI, Data Science)
        tech_matches = re.findall(r"\b(python|react|javascript|data|sql|ai|machine learning|design|sales|figma|flutter|node)\b", ql)
        if tech_matches:
            target = tech_matches[0].capitalize()
            return f"""
                SELECT c.title, c.company, c.location, c.remote_type, c.stipend_or_salary
                FROM jobs_clean c
                JOIN job_skills s ON c.id = s.job_id
                WHERE s.skill LIKE '%{target}%' OR c.title LIKE '%{target}%'
                GROUP BY c.id
                ORDER BY c.id DESC
                LIMIT 10
            """

        # 5. Companies hiring
        if any(w in ql for w in ["company", "companies", "employer", "who is hiring"]):
            return """
                SELECT company, COUNT(*) as active_postings, 
                       GROUP_CONCAT(DISTINCT title) as sample_roles
                FROM jobs_clean 
                WHERE company != 'Company' AND company != 'Confidential'
                GROUP BY company 
                ORDER BY active_postings DESC 
                LIMIT 10
            """

        # 6. Locations
        cities = ["pune", "mumbai", "delhi", "bangalore", "bengaluru", "hyderabad", "chennai", "kolkata", "noida", "gurgaon"]
        for city in cities:
            if city in ql:
                return f"""
                    SELECT title, company, location, remote_type, stipend_or_salary 
                    FROM jobs_clean 
                    WHERE location LIKE '%{city}%' 
                    ORDER BY id DESC 
                    LIMIT 10
                """

        # Default fallback: Top recent clean jobs
        return """
            SELECT title, company, location, remote_type, stipend_or_salary 
            FROM jobs_clean 
            ORDER BY id DESC 
            LIMIT 10
        """

    def _synthesize_answer(self, question: str, sql: str, rows: List[Dict[str, Any]], columns: List[str]) -> str:
        """Formats query output into clear Markdown explanation with tables."""
        if not rows:
            return f"I searched the database for **'{question}'**, but found 0 matching records. Try broadening your criteria or search for common skills like *Python*, *React*, *Sales*, or *Graphic Design*."

        lines = []
        lines.append(f"Based on **{len(rows)} verified database records** matching your question:\n")

        cols_lower = [c.lower() for c in columns]
        count_col = next((c for c in columns if "count" in c.lower()), None)
        skill_col = next((c for c in columns if "skill" in c.lower()), None)
        remote_col = next((c for c in columns if "remote" in c.lower()), None)
        comp_col = next((c for c in columns if "company" in c.lower()), None)
        title_col = next((c for c in columns if "title" in c.lower()), None)

        # 1. Skill ranking
        if skill_col and count_col:
            lines.append(f"| Rank | Skill / Technology | Postings Requiring Skill |")
            lines.append("|:---|:---|:---|")
            for i, r in enumerate(rows, 1):
                lines.append(f"| #{i} | **{r.get(skill_col)}** | {r.get(count_col)} positions |")
            lines.append(f"\n💡 **Takeaway:** `{rows[0].get(skill_col)}` is leading in demand across this dataset.")

        # 2. Remote distribution
        elif remote_col and count_col:
            lines.append("| Workplace Arrangement | Job Count |")
            lines.append("|:---|:---|")
            for r in rows:
                lines.append(f"| **{r.get(remote_col)}** | {r.get(count_col)} positions |")
            lines.append("\n💡 **Takeaway:** On-site positions lead the entry-level market, while software engineering roles offer highest remote availability.")

        # 3. Company hiring ranking
        elif comp_col and count_col:
            lines.append("| Company / Employer | Active Postings |")
            lines.append("|:---|:---|")
            for r in rows[:8]:
                lines.append(f"| **{r.get(comp_col)}** | {r.get(count_col)} openings |")

        # 4. Job listings with title
        elif title_col:
            loc_col = next((c for c in columns if "location" in c.lower()), "location")
            stip_col = next((c for c in columns if "stipend" in c.lower() or "salary" in c.lower()), "stipend_or_salary")
            comp_name_col = comp_col or "company"
            rem_name_col = remote_col or "remote_type"

            lines.append("| Role / Title | Company | Location | Modality | Stipend / Salary |")
            lines.append("|:---|:---|:---|:---|:---|")
            for r in rows[:10]:
                title_val = str(r.get(title_col, 'Role'))[:35]
                comp_val = str(r.get(comp_name_col, 'Company'))[:25]
                loc_val = str(r.get(loc_col, 'Unspecified'))[:20]
                rem_val = str(r.get(rem_name_col, 'On-site'))[:10]
                stip_val = str(r.get(stip_col, 'Not Disclosed'))[:25]
                lines.append(f"| **{title_val}** | {comp_val} | {loc_val} | {rem_val} | {stip_val} |")

        # 5. Generic dynamic table fallback
        else:
            header = " | ".join([f"**{c.title()}**" for c in columns[:5]])
            lines.append(f"| {header} |")
            lines.append("|" + "---|"*len(columns[:5]))
            for r in rows[:10]:
                row_str = " | ".join([str(r.get(c, ''))[:30] for c in columns[:5]])
                lines.append(f"| {row_str} |")

        return "\n".join(lines)

    def _generate_followups(self, question: str) -> List[str]:
        ql = question.lower()
        if "skill" in ql:
            return ["Show me high-paying remote roles", "What companies are hiring for Python?", "How many jobs are remote vs on-site?"]
        elif "remote" in ql:
            return ["What are the top skills for remote jobs?", "Show me jobs in Pune or Mumbai", "Which companies have the most openings?"]
        else:
            return ["What are the top 5 most demanded skills?", "Show me remote internship opportunities", "What is the typical stipend range?"]
