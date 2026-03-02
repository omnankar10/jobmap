"""Greenhouse job board ingestion connector."""
import re
import logging
from datetime import datetime
from typing import List, Optional
from html import unescape

import httpx
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.models import Job, Company, IngestionRun
from app.services.geocoder import geocode_job

logger = logging.getLogger(__name__)

# Well-known Greenhouse board tokens for MVP seed data
DEFAULT_BOARDS = [
    "stripe",
    "figma",
    "gitlab",
    "notion",
    "airbnb",
    "canva",
    "databricks",
    "coinbase",
    "discord",
    "ramp",
    # Fintech
    "plaid",
    "brex",
    "chime",
    "robinhood",
    "affirm",
    "wise",
    "checkoutcom",

    # AI / Data / Infra
    "openai",
    "anthropic",
    "scaleai",
    "huggingface",
    "confluent",
    "snowflake",
    "mongodb",
    "elastic",
    "cloudflare",

    # SaaS / Product
    "asana",
    "atlassian",
    "mondaycom",
    "hubspot",
    "zapier",
    "dropbox",
    "intercom",
    "loom",

    # DevTools
    "vercel",
    "supabase",
    "hashicorp",
    "datadog",
    "newrelic",

    # HealthTech
    "hims",
    "headspace",
    "ro",
    "talkspace",

    # E-commerce / Marketplace
    "shopify",
    "instacart",
    "doordash",
    "etsy",
]

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"

# Simple tag dictionary for extraction
TAG_KEYWORDS = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "react": "react",
    "node": "node.js",
    "sql": "sql",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "machine learning": "machine-learning",
    "ml": "machine-learning",
    "deep learning": "deep-learning",
    "data science": "data-science",
    "devops": "devops",
    "go": "golang",
    "golang": "golang",
    "rust": "rust",
    "c++": "c++",
    "ruby": "ruby",
    "rails": "ruby-on-rails",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "spark": "apache-spark",
    "hadoop": "hadoop",
    "terraform": "terraform",
    "figma": "design",
    "product design": "product-design",
    "ux": "ux-design",
    "ui": "ui-design",
    "frontend": "frontend",
    "backend": "backend",
    "full stack": "full-stack",
    "fullstack": "full-stack",
    "data engineer": "data-engineering",
    "analytics": "analytics",
    "security": "security",
    "ios": "ios",
    "android": "android",
    "mobile": "mobile",
}


def _strip_html(html_str: str) -> str:
    """Convert HTML to plain text."""
    if not html_str:
        return ""
    text = re.sub(r"<[^>]+>", " ", html_str)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_tags(title: str, description: str, department: str = "") -> List[str]:
    """Extract tags from title, description, and department using keyword matching."""
    combined = f"{title} {department} {description}".lower()
    found = set()
    for keyword, tag in TAG_KEYWORDS.items():
        if keyword in combined:
            found.add(tag)
    return sorted(found)


def _fetch_board_jobs(token: str) -> List[dict]:
    """Fetch jobs from a Greenhouse board by token."""
    url = GREENHOUSE_API.format(token=token)
    try:
        resp = httpx.get(url, params={"content": "true"}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobs", [])
    except httpx.HTTPError as e:
        logger.warning(f"Failed to fetch Greenhouse board '{token}': {e}")
        return []


def _get_or_create_company(db: Session, name: str) -> Company:
    """Get existing company by name or create a new one."""
    company = db.query(Company).filter(Company.name == name).first()
    if not company:
        company = Company(name=name)
        db.add(company)
        db.flush()
    return company


def run_greenhouse_ingestion(db: Session, boards: Optional[List[str]] = None) -> IngestionRun:
    """
    Run Greenhouse ingestion for the specified board tokens.
    Returns the IngestionRun record.
    """
    if boards is None:
        boards = DEFAULT_BOARDS

    run = IngestionRun(source="greenhouse")
    db.add(run)
    db.flush()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    errors = []

    for token in boards:
        logger.info(f"Fetching jobs from Greenhouse board: {token}")
        try:
            raw_jobs = _fetch_board_jobs(token)
            total_fetched += len(raw_jobs)

            # Company name from board token (capitalize)
            company_name = token.replace("-", " ").title()
            company = _get_or_create_company(db, company_name)

            for raw in raw_jobs:
                try:
                    source_job_id = str(raw.get("id", ""))
                    title = raw.get("title", "Untitled")
                    description_html = raw.get("content", "")
                    description_text = _strip_html(description_html)
                    apply_url = raw.get("absolute_url", "")
                    if not apply_url:
                        continue

                    # Location
                    location_text = raw.get("location", {}).get("name", "")

                    # Department / tags
                    departments = raw.get("departments", [])
                    dept_name = departments[0].get("name", "") if departments else ""
                    tags = _extract_tags(title, description_text, dept_name)

                    # Posted date
                    updated_at = raw.get("updated_at")
                    posted_at = None
                    if updated_at:
                        try:
                            posted_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        except (ValueError, TypeError):
                            pass

                    # Check if exists
                    existing = db.query(Job).filter(
                        Job.source == "greenhouse",
                        Job.source_job_id == source_job_id,
                    ).first()

                    if existing:
                        # Update
                        existing.title = title
                        existing.description_html = description_html
                        existing.description_text = description_text
                        existing.apply_url = apply_url
                        existing.location_text = location_text
                        existing.tags = tags
                        existing.posted_at = posted_at
                        existing.scraped_at = datetime.utcnow()
                        existing.is_active = True
                        geocode_job(existing, db)
                        total_updated += 1
                    else:
                        # Insert
                        job = Job(
                            source="greenhouse",
                            source_job_id=source_job_id,
                            company_id=company.id,
                            title=title,
                            description_html=description_html,
                            description_text=description_text,
                            apply_url=apply_url,
                            location_text=location_text,
                            tags=tags,
                            posted_at=posted_at,
                            scraped_at=datetime.utcnow(),
                        )
                        geocode_job(job, db)
                        db.add(job)
                        total_inserted += 1

                except Exception as e:
                    logger.error(f"Error processing job in board '{token}': {e}")
                    errors.append({"board": token, "error": str(e)})

            db.commit()

        except Exception as e:
            logger.error(f"Error processing board '{token}': {e}")
            errors.append({"board": token, "error": str(e)})
            db.rollback()

    run.ended_at = datetime.utcnow()
    run.status = "success" if not errors else "partial"
    run.jobs_fetched = total_fetched
    run.jobs_inserted = total_inserted
    run.jobs_updated = total_updated
    run.errors = errors if errors else None
    db.commit()

    logger.info(
        f"Greenhouse ingestion complete: fetched={total_fetched}, "
        f"inserted={total_inserted}, updated={total_updated}, errors={len(errors)}"
    )
    return run
