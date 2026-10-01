import re
from typing import Dict, List, Any
from db.database import get_unparsed_raw_jobs, insert_clean_job_record

# Comprehensive canonical skills dictionary for tech & business roles
SKILL_PATTERNS = [
    # Programming Languages
    r"\bPython\b", r"\bJava\b", r"\bC\+\+\b", r"\bC#\b", r"\bJavaScript\b", r"\bTypeScript\b",
    r"\bGo\b|\bGolang\b", r"\bRust\b", r"\bPHP\b", r"\bRuby\b", r"\bKotlin\b", r"\bSwift\b", r"\bSQL\b",
    # Web & Full Stack
    r"\bReact(?:\.js)?\b", r"\bAngular\b", r"\bVue(?:\.js)?\b", r"\bNode(?:\.js)?\b", r"\bNext(?:\.js)?\b",
    r"\bDjango\b", r"\bFastAPI\b", r"\bFlask\b", r"\bSpring(?:\s*Boot)?\b", r"\bHTML5?\b", r"\bCSS3?\b",
    # Data & AI
    r"\bMachine Learning\b|\bML\b", r"\bDeep Learning\b", r"\bNLP\b", r"\bComputer Vision\b",
    r"\bPyTorch\b", r"\bTensorFlow\b", r"\bData Analysis\b", r"\bPandas\b", r"\bNumPy\b",
    r"\bPower BI\b", r"\bTableau\b", r"\bExcel\b", r"\bLLM\b|\bGenerative AI\b",
    # Cloud & DevOps
    r"\bAWS\b", r"\bAzure\b", r"\bGCP\b|\bGoogle Cloud\b", r"\bDocker\b", r"\bKubernetes\b|\bK8s\b",
    r"\bCI/CD\b", r"\bLinux\b", r"\bGit\b",
    # Product & Business
    r"\bFigma\b", r"\bUI/UX\b", r"\bGraphic Design\b", r"\bSales\b", r"\bBusiness Development\b",
    r"\bDigital Marketing\b", r"\bSEO\b", r"\bContent Writing\b", r"\bSocial Media\b"
]

COMPILED_SKILLS = [(re.compile(p, re.IGNORECASE), p.replace(r"\b", "").replace(r"\s*", " ").replace(r"(?:\.js)?", "").split("|")[0]) for p in SKILL_PATTERNS]


class JobParserAgent:
    """
    Autonomous parsing agent that converts messy, unstructured raw job postings
    into clean, normalized relational job records with skill tagging.
    """

    def parse_internshala_text(self, text: str) -> Dict[str, Any]:
        """Specialized high-accuracy parser for Internshala structured strings."""
        title_m = re.search(r"Title:\s*([^|]+)", text)
        company_m = re.search(r"Company:\s*([^|]+)", text)
        loc_m = re.search(r"Location:\s*([^|]+)", text)
        stipend_m = re.search(r"Stipend:\s*([^|]+)", text)

        title = title_m.group(1).strip() if title_m else "Internship Role"
        company = company_m.group(1).strip() if company_m else "Company"
        
        # Clean location from format like "[['Pune']]"
        raw_loc = loc_m.group(1).strip() if loc_m else "Unspecified"
        cleaned_loc = re.sub(r"[\[\]']", "", raw_loc).strip() or "Unspecified"
        if "remote" in cleaned_loc.lower() or "work from home" in cleaned_loc.lower():
            remote_type = "Remote"
        elif "hybrid" in cleaned_loc.lower():
            remote_type = "Hybrid"
        else:
            remote_type = "On-site"

        stipend = stipend_m.group(1).strip() if stipend_m else "Unpaid / Not Disclosed"
        # Fix non-breaking space issues
        stipend = stipend.replace("\xa0", " ").strip()

        skills = self.extract_skills(f"{title} {text}")

        # Comprehensive skill inference based on title keywords
        title_lower = title.lower()
        if "sales" in title_lower or "business development" in title_lower:
            skills.extend(["Sales", "Business Development"])
        if "graphic" in title_lower or "design" in title_lower:
            skills.extend(["Graphic Design", "UI/UX"])
        if "ui/ux" in title_lower or "product design" in title_lower:
            skills.extend(["UI/UX", "Figma"])
        if "python" in title_lower:
            skills.append("Python")
        if "content" in title_lower:
            skills.append("Content Writing")
        if "digital marketing" in title_lower or "marketing" in title_lower:
            skills.append("Digital Marketing")
        if "social media" in title_lower:
            skills.extend(["Social Media Marketing", "Digital Marketing"])
        if "seo" in title_lower:
            skills.extend(["SEO", "Digital Marketing"])
        if "web develop" in title_lower or "web design" in title_lower:
            skills.extend(["Web Development", "JavaScript", "HTML/CSS"])
        if "front end" in title_lower or "frontend" in title_lower:
            skills.extend(["Frontend", "JavaScript", "React"])
        if "backend" in title_lower or "back end" in title_lower:
            skills.extend(["Backend", "Node.js", "SQL"])
        if "full stack" in title_lower or "fullstack" in title_lower:
            skills.extend(["Full Stack", "JavaScript", "Python"])
        if "data" in title_lower and ("analyst" in title_lower or "science" in title_lower or "analytics" in title_lower):
            skills.extend(["Data Analytics", "Python", "SQL", "Excel"])
        if "machine learning" in title_lower or "ai" in title_lower or "artificial intelligence" in title_lower:
            skills.extend(["Machine Learning", "Python", "Deep Learning"])
        if "video" in title_lower or "animation" in title_lower:
            skills.append("Video Editing")
        if "hr" in title_lower or "human resource" in title_lower:
            skills.append("Human Resources")
        if "flutter" in title_lower:
            skills.extend(["Flutter", "Mobile App Development"])
        if "android" in title_lower:
            skills.extend(["Android", "Mobile App Development"])
        if "react" in title_lower:
            skills.append("React")
        if "node" in title_lower:
            skills.append("Node.js")
        if "market research" in title_lower:
            skills.extend(["Market Research", "Data Analysis"])
        if "operations" in title_lower:
            skills.append("Operations Management")

        return {
            "title": title,
            "company": company,
            "location": cleaned_loc,
            "remote_type": remote_type,
            "job_level": "Internship",
            "stipend_or_salary": stipend,
            "posted_date": "2026-09-30",
            "skills": list(set(skills))
        }

    def parse_generic_text(self, text: str) -> Dict[str, Any]:
        """Parser for HackerNews or unstructured web text postings."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_line = lines[0] if lines else text[:100]

        # HN format often: Company | Title | Location | Remote/ONSITE | Salary
        parts = [p.strip() for p in first_line.split("|")]
        company = parts[0] if len(parts) > 0 and len(parts[0]) < 50 else "Tech Company"
        title = parts[1] if len(parts) > 1 and len(parts[1]) < 60 else "Software Engineer"
        location = parts[2] if len(parts) > 2 and len(parts[2]) < 40 else "San Francisco / Remote"

        text_lower = text.lower()
        remote_type = "Remote" if "remote" in text_lower else ("Hybrid" if "hybrid" in text_lower else "On-site")
        job_level = "Senior" if "senior" in text_lower or "lead" in text_lower or "staff" in text_lower else ("Internship" if "intern" in text_lower else "Mid-Level")

        # Salary detection
        salary_match = re.search(r"(\$\d+k?\s*-\s*\$\d+k?|\$\d+,\d{3}|\$\d+k|\b\d+k\s*-\s*\d+k\b)", text, re.IGNORECASE)
        salary = salary_match.group(1) if salary_match else "Competitive / Equity"

        skills = self.extract_skills(text)

        return {
            "title": title,
            "company": company,
            "location": location,
            "remote_type": remote_type,
            "job_level": job_level,
            "stipend_or_salary": salary,
            "posted_date": "2026-09-30",
            "skills": skills
        }

    def extract_skills(self, text: str) -> List[str]:
        """Extracts tech and business skills via pattern matching."""
        found = []
        for pattern, skill_name in COMPILED_SKILLS:
            if pattern.search(text):
                found.append(skill_name)
        return list(set(found))

    def process_unparsed_jobs(self, batch_size: int = 100) -> int:
        """Pulls unparsed raw jobs and populates jobs_clean and job_skills."""
        unparsed = get_unparsed_raw_jobs(limit=batch_size)
        if not unparsed:
            print("[*] No unparsed raw jobs found in jobs_raw.")
            return 0

        print(f"[+] [Parser Agent] Processing batch of {len(unparsed)} unparsed job postings...")
        parsed_count = 0

        for row in unparsed:
            raw_id = row["id"]
            source = row["source"]
            raw_text = row["raw_text"] or ""

            if source == "internshala_dataset" or "Stipend:" in raw_text:
                parsed = self.parse_internshala_text(raw_text)
            else:
                parsed = self.parse_generic_text(raw_text)

            insert_clean_job_record(
                raw_id=raw_id,
                title=parsed["title"],
                company=parsed["company"],
                location=parsed["location"],
                remote_type=parsed["remote_type"],
                job_level=parsed["job_level"],
                stipend_or_salary=parsed["stipend_or_salary"],
                posted_date=parsed["posted_date"],
                skills=parsed["skills"]
            )
            parsed_count += 1

        print(f"[OK] [Parser Agent] Successfully cleaned and tagged {parsed_count} job postings.")
        return parsed_count
