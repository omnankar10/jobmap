"""SQLAlchemy ORM models matching the AGENT.md schema."""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime,
    ForeignKey, Float, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from geoalchemy2 import Geography
from sqlalchemy.orm import relationship
from app.db.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, unique=True, nullable=False)
    website = Column(Text, nullable=True)
    logo_url = Column(Text, nullable=True)
    industry = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    source_job_id = Column(Text, nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    title = Column(Text, nullable=False)
    description_html = Column(Text, nullable=True)
    description_text = Column(Text, nullable=True)
    apply_url = Column(Text, nullable=False)
    employment_type = Column(Text, nullable=True)
    remote_type = Column(Text, nullable=False, default="onsite")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    salary_currency = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    location_text = Column(Text, nullable=True)
    country = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    geo = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    is_active = Column(Boolean, default=True)

    company = relationship("Company", back_populates="jobs")

    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_source_job"),
        Index("ix_jobs_posted_at", "posted_at"),
        Index("ix_jobs_geo", "geo", postgresql_using="gist"),
        Index("ix_jobs_tags", "tags", postgresql_using="gin"),
    )


class GeocodeCache(Base):
    __tablename__ = "geocode_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, unique=True, nullable=False)
    city = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
    country = Column(Text, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    geo = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    raw_response = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(Text, default="running")
    jobs_fetched = Column(Integer, default=0)
    jobs_inserted = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    errors = Column(JSONB, nullable=True)
