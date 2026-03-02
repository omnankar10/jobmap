"""Pydantic schemas for API request/response models."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# --- Response Models ---

class CompanyOut(BaseModel):
    id: UUID
    name: str
    website: Optional[str] = None
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class JobListItem(BaseModel):
    id: UUID
    title: str
    company: Optional[CompanyOut] = None
    remote_type: str
    location_text: Optional[str] = None
    posted_at: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    tags: Optional[List[str]] = None

    class Config:
        from_attributes = True


class JobDetail(BaseModel):
    id: UUID
    title: str
    company: Optional[CompanyOut] = None
    source: str
    remote_type: str
    location_text: Optional[str] = None
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    posted_at: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    tags: Optional[List[str]] = None
    description_html: Optional[str] = None
    description_text: Optional[str] = None
    apply_url: str
    employment_type: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class JobsResponse(BaseModel):
    items: List[JobListItem]
    meta: dict


class ClusterItem(BaseModel):
    lat: float
    lng: float
    count: int
    bbox: Optional[List[float]] = None  # [minLng, minLat, maxLng, maxLat]


class ClustersResponse(BaseModel):
    clusters: List[ClusterItem]
    points: List[JobListItem]


class IngestionRunOut(BaseModel):
    id: UUID
    source: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    jobs_fetched: int
    jobs_inserted: int
    jobs_updated: int

    class Config:
        from_attributes = True
