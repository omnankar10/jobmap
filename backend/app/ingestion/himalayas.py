"""Himalayas.app job board ingestion connector (free JSON API, no key needed).
Endpoint: https://himalayas.app/jobs/api
Returns remote jobs with HTML descriptions, salary data, and company info.
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

HIMALAYAS_URL = "https://himalayas.app/jobs/api"

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


def _extract_tags(title: str, description: str, categories: list = None) -> List[str]:
    found = set()
    if categories:
        for c in categories:
            found.add(c.lower().replace(" ", "-"))
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


def run_himalayas_ingestion(db: Session) -> IngestionRun:
    """Fetch jobs from Himalayas free API (paginated, 20 per page)."""
    run = IngestionRun(source="himalayas")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    try:
        offset = 0
        max_pages = 5
        page = 0

        while page < max_pages:
            resp = httpx.get(
                HIMALAYAS_URL,
                params={"limit": 20, "offset": offset},
                timeout=30,
                headers={"User-Agent": "jobmap-mvp/0.1"},
            )
            resp.raise_for_status()
            data = resp.json()
            jobs_data = data if isinstance(data, list) else data.get("jobs", data.get("data", []))
            if not jobs_data:
                break

            total_fetched += len(jobs_data)

            for raw in jobs_data:
                try:
                    source_job_id = str(raw.get("guid", raw.get("id", "")))
                    if not source_job_id:
                        continue

                    company_name = raw.get("companyName", "Unknown")
                    title = raw.get("title", "Untitled")
                    description_html = raw.get("description", "")
                    description_text = _strip_html(description_html)
                    apply_url = raw.get("applicationLink", raw.get("url", ""))
                    if not apply_url:
                        continue

                    # Location from locationRestrictions
                    location_parts = raw.get("locationRestrictions", [])
                    location_text = ", ".join(location_parts) if location_parts else "Remote"

                    categories = raw.get("categories", raw.get("parentCategories", []))
                    tags = _extract_tags(title, description_text, categories)

                    # Salary
                    salary_min = raw.get("minSalary")
                    salary_max = raw.get("maxSalary")
                    salary_currency = raw.get("currency", "USD")

                    # Parse date
                    posted_at = None
                    pub_date = raw.get("pubDate")
                    if pub_date:
                        try:
                            posted_at = datetime.fromtimestamp(pub_date / 1000 if pub_date > 1e10 else pub_date)
                        except (ValueError, TypeError, OSError):
                            pass

                    company = _get_or_create_company(db, company_name)

                    existing = db.query(Job).filter(
                        Job.source == "himalayas",
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
                        existing.salary_currency = salary_currency
                        existing.scraped_at = datetime.utcnow()
                        existing.is_active = True
                        geocode_job(existing, db)
                        total_updated += 1
                    else:
                        job = Job(
                            source="himalayas",
                            source_job_id=source_job_id,
                            company_id=company.id,
                            title=title,
                            description_html=description_html,
                            description_text=description_text,
                            apply_url=apply_url,
                            remote_type="remote",
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
                    logger.error(f"Error processing Himalayas job: {e}")
                    errors.append({"error": str(e)})

            db.commit()
            offset += 20
            page += 1

    except Exception as e:
        logger.error(f"Himalayas ingestion error: {e}")
        errors.append({"error": str(e)})
        db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(f"Himalayas ingestion: fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}")
    return run
