"""Arbeitnow job board ingestion connector (free JSON API, no key needed)."""
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

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

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


def run_arbeitnow_ingestion(db: Session) -> IngestionRun:
    """Fetch jobs from Arbeitnow free API (paginated)."""
    run = IngestionRun(source="arbeitnow")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    try:
        page = 1
        max_pages = 3  # Limit pages for MVP

        while page <= max_pages:
            resp = httpx.get(
                ARBEITNOW_URL,
                params={"page": page},
                timeout=30,
                headers={"User-Agent": "jobmap-mvp/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()
            jobs_data = data.get("data", [])
            if not jobs_data:
                break

            total_fetched += len(jobs_data)

            for raw in jobs_data:
                try:
                    source_job_id = str(raw.get("slug", raw.get("url", "")))
                    if not source_job_id:
                        continue

                    company_name = raw.get("company_name", "Unknown")
                    title = raw.get("title", "Untitled")
                    description_html = raw.get("description", "")
                    description_text = _strip_html(description_html)
                    apply_url = raw.get("url", "")
                    if not apply_url:
                        continue

                    location_text = raw.get("location", "")
                    remote = raw.get("remote", False)
                    source_tags = raw.get("tags", [])
                    tags = _extract_tags(title, description_text, source_tags)

                    posted_at = None
                    created_at = raw.get("created_at")
                    if created_at:
                        try:
                            posted_at = datetime.fromtimestamp(created_at)
                        except (ValueError, TypeError, OSError):
                            pass

                    company = _get_or_create_company(db, company_name)

                    existing = db.query(Job).filter(
                        Job.source == "arbeitnow",
                        Job.source_job_id == source_job_id,
                    ).first()

                    remote_type = "remote" if remote else "onsite"

                    if existing:
                        existing.title = title
                        existing.description_html = description_html
                        existing.description_text = description_text
                        existing.apply_url = apply_url
                        existing.location_text = location_text
                        existing.remote_type = remote_type
                        existing.tags = tags
                        existing.posted_at = posted_at
                        existing.scraped_at = datetime.utcnow()
                        existing.is_active = True
                        geocode_job(existing, db)
                        total_updated += 1
                    else:
                        job = Job(
                            source="arbeitnow",
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
                            scraped_at=datetime.utcnow(),
                        )
                        geocode_job(job, db)
                        db.add(job)
                        total_inserted += 1

                except Exception as e:
                    logger.error(f"Error processing Arbeitnow job: {e}")
                    errors.append({"error": str(e)})

            db.commit()

            # Check if more pages exist
            meta = data.get("meta", {})
            if page >= meta.get("last_page", 1):
                break
            page += 1

    except Exception as e:
        logger.error(f"Arbeitnow ingestion error: {e}")
        errors.append({"error": str(e)})
        db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(f"Arbeitnow ingestion: fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}")
    return run
