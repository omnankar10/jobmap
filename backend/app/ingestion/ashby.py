"""Ashby job board ingestion connector (free public posting API, no key needed).
Endpoint: https://api.ashbyhq.com/posting-api/job-board/{BOARD_NAME}
Each company has its own board. We scrape a curated list of known boards.
"""
import re
import logging
from datetime import datetime
from html import unescape
from typing import List

import httpx
from sqlalchemy.orm import Session

from app.models.models import Job, Company, IngestionRun
from app.services.geocoder import geocode_job

logger = logging.getLogger(__name__)

ASHBY_API_BASE = "https://api.ashbyhq.com/posting-api/job-board"

# Well-known companies using Ashby for their job boards
ASHBY_BOARDS = [
    "Ramp",
    "Notion",
    "Vercel",
    "Linear",
    "Mercury",
    "OpenAI",
    "Retool",
    "Plaid",
]

TAG_KEYWORDS = {
    "python": "python", "java": "java", "javascript": "javascript",
    "typescript": "typescript", "react": "react", "node": "node.js",
    "sql": "sql", "aws": "aws", "gcp": "gcp", "docker": "docker",
    "kubernetes": "kubernetes", "machine learning": "machine-learning",
    "golang": "golang", "rust": "rust", "ruby": "ruby",
    "swift": "swift", "kotlin": "kotlin", "scala": "scala",
    "devops": "devops", "frontend": "frontend", "backend": "backend",
    "full stack": "full-stack", "fullstack": "full-stack",
    "data engineer": "data-engineering", "ios": "ios", "android": "android",
    "security": "security", "design": "design", "marketing": "marketing",
    "sales": "sales", "product": "product-management",
}


def _strip_html(html_str: str) -> str:
    if not html_str:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_tags(title: str, description: str, department: str = None) -> List[str]:
    found = set()
    if department:
        found.add(department.lower().replace(" ", "-"))
    combined = f"{title} {description}".lower()
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword in combined:
            found.add(tag)
    return sorted(found)[:10]


def _get_or_create_company(db: Session, name: str) -> Company:
    company = db.query(Company).filter(Company.name == name).first()
    if not company:
        company = Company(name=name)
        db.add(company)
        db.flush()
    return company


def run_ashby_ingestion(db: Session) -> IngestionRun:
    """Fetch jobs from Ashby public posting API for known company boards."""
    run = IngestionRun(source="ashby")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    for board_name in ASHBY_BOARDS:
        try:
            url = f"{ASHBY_API_BASE}/{board_name}"
            resp = httpx.get(
                url,
                params={"includeCompensation": "true"},
                timeout=30,
                headers={"User-Agent": "jobmap-mvp/0.1"},
            )
            if resp.status_code == 404:
                logger.warning(f"Ashby board not found: {board_name}")
                continue
            resp.raise_for_status()
            data = resp.json()
            jobs_data = data.get("jobs", [])
            total_fetched += len(jobs_data)

            company = _get_or_create_company(db, board_name)

            for raw in jobs_data:
                try:
                    source_job_id = str(raw.get("id", ""))
                    if not source_job_id:
                        continue

                    title = raw.get("title", "Untitled")
                    description_html = raw.get("descriptionHtml", raw.get("description", ""))
                    description_text = _strip_html(description_html)
                    department = raw.get("department", "")
                    tags = _extract_tags(title, description_text, department)

                    # Location
                    location_text = raw.get("location", "")
                    is_remote = raw.get("isRemote", False)
                    if not location_text and is_remote:
                        location_text = "Remote"

                    # Remote type
                    remote_type = "remote" if is_remote else "onsite"
                    if location_text and is_remote and any(w in location_text.lower() for w in ["hybrid", "office"]):
                        remote_type = "hybrid"

                    # Apply URL
                    apply_url = raw.get("jobUrl", raw.get("applyUrl", ""))
                    if not apply_url:
                        apply_url = f"https://jobs.ashbyhq.com/{board_name}/{source_job_id}"

                    # Published date
                    posted_at = None
                    pub_date = raw.get("publishedAt", raw.get("updatedAt", ""))
                    if pub_date:
                        try:
                            posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                    # Compensation
                    salary_min = None
                    salary_max = None
                    salary_currency = "USD"
                    compensation = raw.get("compensation")
                    if compensation:
                        comp_ranges = compensation.get("compensationTierSummary", "")
                        salary_currency = compensation.get("currency", "USD")
                        # Try to extract min/max from ranges
                        if isinstance(compensation, dict):
                            salary_min = compensation.get("min")
                            salary_max = compensation.get("max")

                    existing = db.query(Job).filter(
                        Job.source == "ashby",
                        Job.source_job_id == source_job_id,
                    ).first()

                    if existing:
                        existing.title = title
                        existing.description_html = description_html
                        existing.description_text = description_text
                        existing.apply_url = apply_url
                        existing.location_text = location_text
                        existing.remote_type = remote_type
                        existing.tags = tags
                        existing.posted_at = posted_at
                        existing.salary_min = salary_min
                        existing.salary_max = salary_max
                        existing.salary_currency = salary_currency
                        existing.scraped_at = datetime.utcnow()
                        existing.is_active = True
                        geocode_job(existing, db)
                        total_updated += 1
                    else:
                        job = Job(
                            source="ashby",
                            source_job_id=source_job_id,
                            company_id=company.id,
                            title=title,
                            description_html=description_html,
                            description_text=description_text,
                            apply_url=apply_url,
                            remote_type=remote_type,
                            location_text=location_text,
                            tags=tags,
                            posted_at=posted_at,
                            salary_min=salary_min,
                            salary_max=salary_max,
                            salary_currency=salary_currency,
                            scraped_at=datetime.utcnow(),
                        )
                        geocode_job(job, db)
                        db.add(job)
                        total_inserted += 1

                except Exception as e:
                    logger.error(f"Error processing Ashby job from {board_name}: {e}")
                    errors.append({"board": board_name, "error": str(e)})

            db.commit()
            logger.info(f"Ashby board '{board_name}': {len(jobs_data)} jobs")

        except Exception as e:
            logger.error(f"Ashby board '{board_name}' error: {e}")
            errors.append({"board": board_name, "error": str(e)})
            db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(f"Ashby ingestion: fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}")
    return run
