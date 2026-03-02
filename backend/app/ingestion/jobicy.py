"""Jobicy job board ingestion connector (free JSON API, no key needed).
Endpoint: https://jobicy.com/api/v2/remote-jobs
Returns remote jobs with descriptions, company info, and geographic data.
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

JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"

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


def _extract_tags(title: str, description: str, industry: str = None) -> List[str]:
    found = set()
    if industry:
        found.add(industry.lower().replace(" ", "-"))
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


def run_jobicy_ingestion(db: Session) -> IngestionRun:
    """Fetch jobs from Jobicy free API (max 50 per request)."""
    run = IngestionRun(source="jobicy")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    try:
        resp = httpx.get(
            JOBICY_URL,
            params={"count": 50},
            timeout=30,
            headers={"User-Agent": "jobmap-mvp/0.1"},
        )
        resp.raise_for_status()
        data = resp.json()
        jobs_data = data.get("jobs", [])
        total_fetched = len(jobs_data)

        for raw in jobs_data:
            try:
                source_job_id = str(raw.get("id", ""))
                if not source_job_id:
                    continue

                company_name = raw.get("companyName", "Unknown")
                title = raw.get("jobTitle", "Untitled")
                description_html = raw.get("jobDescription", "")
                description_text = _strip_html(description_html)
                apply_url = raw.get("url", "")
                if not apply_url:
                    continue

                # Location / geo
                location_text = raw.get("jobGeo", "Remote")
                industry = raw.get("jobIndustry", None)
                if isinstance(industry, list):
                    industry = industry[0] if industry else None
                job_type = raw.get("jobType", "")
                tags = _extract_tags(title, description_text, industry)

                # Salary
                salary_min = None
                salary_max = None
                ann_salary_min = raw.get("annualSalaryMin")
                ann_salary_max = raw.get("annualSalaryMax")
                if ann_salary_min:
                    try:
                        salary_min = int(float(str(ann_salary_min).replace(",", "")))
                    except (ValueError, TypeError):
                        pass
                if ann_salary_max:
                    try:
                        salary_max = int(float(str(ann_salary_max).replace(",", "")))
                    except (ValueError, TypeError):
                        pass
                salary_currency = raw.get("salaryCurrency", "USD")

                # Parse date
                posted_at = None
                pub_date = raw.get("pubDate")
                if pub_date:
                    try:
                        posted_at = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        try:
                            from email.utils import parsedate_to_datetime
                            posted_at = parsedate_to_datetime(pub_date)
                        except:
                            pass

                company = _get_or_create_company(db, company_name)

                existing = db.query(Job).filter(
                    Job.source == "jobicy",
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
                        source="jobicy",
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
                logger.error(f"Error processing Jobicy job: {e}")
                errors.append({"error": str(e)})

        db.commit()

    except Exception as e:
        logger.error(f"Jobicy ingestion error: {e}")
        errors.append({"error": str(e)})
        db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(f"Jobicy ingestion: fetched={total_fetched}, inserted={total_inserted}, updated={total_updated}")
    return run
