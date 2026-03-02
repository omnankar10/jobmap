"""RemoteOK job board ingestion connector (free JSON API, no key needed)."""
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

REMOTEOK_URL = "https://remoteok.com/api"

TAG_KEYWORDS = {
    "python": "python", "java": "java", "javascript": "javascript",
    "typescript": "typescript", "react": "react", "node": "node.js",
    "sql": "sql", "aws": "aws", "gcp": "gcp", "docker": "docker",
    "kubernetes": "kubernetes", "machine learning": "machine-learning",
    "golang": "golang", "go ": "golang", "rust": "rust", "ruby": "ruby",
    "swift": "swift", "kotlin": "kotlin", "scala": "scala",
    "devops": "devops", "frontend": "frontend", "backend": "backend",
    "full stack": "full-stack", "fullstack": "full-stack",
    "data engineer": "data-engineering", "ios": "ios", "android": "android",
    "security": "security", "design": "design",
}


def _strip_html(html_str: str) -> str:
    if not html_str:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_tags(title: str, description: str, source_tags: list = None) -> List[str]:
    found = set()
    if source_tags:
        for t in source_tags:
            found.add(t.lower().replace(" ", "-"))
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


def run_remoteok_ingestion(db: Session) -> IngestionRun:
    """Fetch jobs from RemoteOK free API."""
    run = IngestionRun(source="remoteok")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    try:
        resp = httpx.get(REMOTEOK_URL, timeout=30, headers={"User-Agent": "jobmap-mvp/0.1"})
        resp.raise_for_status()
        data = resp.json()

        # First item is metadata, skip it
        jobs_data = [j for j in data if isinstance(j, dict) and j.get("id")]
        total_fetched = len(jobs_data)

        for raw in jobs_data:
            try:
                source_job_id = str(raw.get("id", ""))
                company_name = raw.get("company", "Unknown")
                title = raw.get("position", "Untitled")
                description_html = raw.get("description", "")
                description_text = _strip_html(description_html)
                apply_url = raw.get("url", raw.get("apply_url", ""))
                if not apply_url:
                    continue

                location_text = raw.get("location", "Remote")
                source_tags = raw.get("tags", [])
                tags = _extract_tags(title, description_text, source_tags)

                # Parse date
                posted_at = None
                date_str = raw.get("date")
                if date_str:
                    try:
                        posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

                # Salary
                salary_min = raw.get("salary_min")
                salary_max = raw.get("salary_max")
                if isinstance(salary_min, str):
                    try:
                        salary_min = int(salary_min)
                    except ValueError:
                        salary_min = None
                if isinstance(salary_max, str):
                    try:
                        salary_max = int(salary_max)
                    except ValueError:
                        salary_max = None

                company = _get_or_create_company(db, company_name)

                existing = db.query(Job).filter(
                    Job.source == "remoteok",
                    Job.source_job_id == source_job_id,
                ).first()

                if existing:
                    existing.title = title
                    existing.description_html = description_html
                    existing.description_text = description_text
                    existing.apply_url = apply_url
                    existing.location_text = location_text
                    existing.tags = tags
                    existing.posted_at = posted_at
                    existing.salary_min = salary_min
                    existing.salary_max = salary_max
                    existing.scraped_at = datetime.utcnow()
                    existing.is_active = True
                    geocode_job(existing, db)
                    total_updated += 1
                else:
                    job = Job(
                        source="remoteok",
                        source_job_id=source_job_id,
                        company_id=company.id,
                        title=title,
                        description_html=description_html,
                        description_text=description_text,
                        apply_url=apply_url,
                        remote_type="remote",  # RemoteOK = all remote
                        location_text=location_text,
                        tags=tags,
                        posted_at=posted_at,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        salary_currency="USD",
                        scraped_at=datetime.utcnow(),
                    )
                    geocode_job(job, db)
                    db.add(job)
                    total_inserted += 1

            except Exception as e:
                logger.error(f"Error processing RemoteOK job: {e}")
                errors.append({"error": str(e)})

        db.commit()

    except Exception as e:
        logger.error(f"RemoteOK ingestion error: {e}")
        errors.append({"error": str(e)})
        db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(f"RemoteOK ingestion: fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}")
    return run
