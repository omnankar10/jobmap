"""Jobs API router with filtering, search, detail, and clustering endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, text, and_, or_, cast, Float
from typing import Optional, List
from uuid import UUID

from app.db.database import get_db
from app.models.models import Job, Company
from app.models.schemas import (
    JobListItem, JobDetail, JobsResponse, CompanyOut,
    ClusterItem, ClustersResponse,
)

router = APIRouter(tags=["jobs"])


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    """Return all companies with job counts for the company filter."""
    results = (
        db.query(Company.id, Company.name, func.count(Job.id).label("job_count"))
        .join(Job, Job.company_id == Company.id)
        .filter(Job.is_active == True)
        .group_by(Company.id, Company.name)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    return [
        {"id": str(r.id), "name": r.name, "job_count": r.job_count}
        for r in results
    ]


@router.get("/countries")
def list_countries(db: Session = Depends(get_db)):
    """Return all countries with job counts for the country filter."""
    results = (
        db.query(Job.country, func.count(Job.id).label("job_count"))
        .filter(Job.is_active == True, Job.country.isnot(None), Job.country != "")
        .group_by(Job.country)
        .order_by(func.count(Job.id).desc())
        .all()
    )
    return [
        {"country": r.country, "job_count": r.job_count}
        for r in results
    ]


@router.get("/jobs", response_model=JobsResponse)
def list_jobs(
    q: Optional[str] = None,
    remote_type: Optional[str] = Query(None, pattern="^(remote|hybrid|onsite|any)$"),
    posted_since: Optional[str] = Query(None, pattern="^(24h|7d|30d|all)$"),
    salary_min: Optional[int] = None,
    salary_max: Optional[int] = None,
    tags: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    company_id: Optional[str] = None,
    bbox: Optional[str] = None,
    limit: int = Query(200, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List jobs with filtering, search, and geospatial bbox."""
    from datetime import datetime, timedelta

    # Base query with lat/lng extracted from geo
    query = db.query(
        Job,
        func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lat"),
        func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lng"),
    ).options(joinedload(Job.company)).filter(Job.is_active == True)

    # Keyword search — checks both full-text search vector AND company name
    if q:
        search_term = q.strip()
        query = query.filter(
            or_(
                text("search_vector @@ plainto_tsquery('english', :q)"),
                Job.company.has(Company.name.ilike(f"%{search_term}%")),
                Job.title.ilike(f"%{search_term}%"),
            )
        ).params(q=search_term)

    # Remote type
    if remote_type and remote_type != "any":
        query = query.filter(Job.remote_type == remote_type)

    # Recency
    if posted_since and posted_since != "all":
        delta_map = {"24h": timedelta(hours=24), "7d": timedelta(days=7), "30d": timedelta(days=30)}
        if posted_since in delta_map:
            cutoff = datetime.utcnow() - delta_map[posted_since]
            query = query.filter(Job.posted_at >= cutoff)

    # Salary
    if salary_min is not None:
        query = query.filter(Job.salary_max >= salary_min)
    if salary_max is not None:
        query = query.filter(Job.salary_min <= salary_max)

    # Tags
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if tag_list:
            query = query.filter(Job.tags.overlap(tag_list))

    # Company filter
    if company_id:
        query = query.filter(Job.company_id == company_id)

    # Location filters
    if country:
        query = query.filter(func.lower(Job.country) == country.lower())
    if region:
        query = query.filter(func.lower(Job.region) == region.lower())
    if city:
        query = query.filter(func.lower(Job.city) == city.lower())

    # Bounding box (minLng,minLat,maxLng,maxLat)
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) == 4:
                min_lng, min_lat, max_lng, max_lat = parts
                envelope = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)
                query = query.filter(
                    func.ST_Intersects(Job.geo, envelope)
                )
        except ValueError:
            pass

    # Count before pagination
    count_query = query.with_entities(func.count(Job.id))
    total = count_query.scalar()

    # Order and paginate
    query = query.order_by(Job.posted_at.desc().nullslast())
    results = query.offset(offset).limit(limit).all()

    items = []
    for job, lat, lng in results:
        item = JobListItem(
            id=job.id,
            title=job.title,
            company=CompanyOut(
                id=job.company.id,
                name=job.company.name,
                website=job.company.website,
                logo_url=job.company.logo_url,
            ) if job.company else None,
            remote_type=job.remote_type,
            location_text=job.location_text,
            posted_at=job.posted_at,
            lat=lat,
            lng=lng,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            tags=job.tags,
        )
        items.append(item)

    return JobsResponse(items=items, meta={"total": total or 0})


@router.get("/jobs/clusters", response_model=ClustersResponse)
def get_clusters(
    bbox: str = Query(..., description="minLng,minLat,maxLng,maxLat"),
    zoom: int = Query(3, ge=0, le=20),
    q: Optional[str] = None,
    remote_type: Optional[str] = None,
    posted_since: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Server-side clustering endpoint. Returns clusters when zoomed out, points when zoomed in."""
    from datetime import datetime, timedelta

    # Parse bbox
    try:
        parts = [float(x) for x in bbox.split(",")]
        min_lng, min_lat, max_lng, max_lat = parts
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid bbox format")

    envelope = func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)

    # If zoomed in enough, return individual points
    if zoom >= 12:
        query = db.query(
            Job,
            func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lat"),
            func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lng"),
        ).options(joinedload(Job.company)).filter(
            Job.is_active == True,
            Job.geo.isnot(None),
            func.ST_Intersects(Job.geo, envelope),
        )

        if q:
            query = query.filter(
                or_(
                    text("search_vector @@ plainto_tsquery('english', :q)"),
                    Job.company.has(Company.name.ilike(f"%{q}%")),
                    Job.title.ilike(f"%{q}%"),
                )
            ).params(q=q)
        if remote_type and remote_type != "any":
            query = query.filter(Job.remote_type == remote_type)
        if tags:
            tag_list = [t.strip().lower() for t in tags.split(",")]
            query = query.filter(Job.tags.overlap(tag_list))

        results = query.limit(500).all()
        points = [
            JobListItem(
                id=j.id, title=j.title,
                company=CompanyOut(id=j.company.id, name=j.company.name) if j.company else None,
                remote_type=j.remote_type, location_text=j.location_text,
                posted_at=j.posted_at, lat=lat, lng=lng,
                salary_min=j.salary_min, salary_max=j.salary_max, tags=j.tags,
            )
            for j, lat, lng in results
        ]
        return ClustersResponse(clusters=[], points=points)

    # Grid-based clustering using PostGIS SnapToGrid
    grid_size = 180.0 / (2 ** zoom)  # Adaptive grid based on zoom

    cluster_query = db.query(
        func.count(Job.id).label("count"),
        func.avg(func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("avg_lat"),
        func.avg(func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("avg_lng"),
        func.min(func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("min_lat"),
        func.max(func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("max_lat"),
        func.min(func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("min_lng"),
        func.max(func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)))).label("max_lng"),
    ).filter(
        Job.is_active == True,
        Job.geo.isnot(None),
        func.ST_Intersects(Job.geo, envelope),
    )

    if q:
        cluster_query = cluster_query.filter(
            or_(
                text("search_vector @@ plainto_tsquery('english', :q)"),
                Job.title.ilike(f"%{q}%"),
            )
        ).params(q=q)
    if remote_type and remote_type != "any":
        cluster_query = cluster_query.filter(Job.remote_type == remote_type)
    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",")]
        cluster_query = cluster_query.filter(Job.tags.overlap(tag_list))

    cluster_query = cluster_query.group_by(
        func.ST_SnapToGrid(
            func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo)),
            grid_size
        )
    )

    results = cluster_query.all()
    clusters = [
        ClusterItem(
            lat=row.avg_lat,
            lng=row.avg_lng,
            count=row.count,
            bbox=[row.min_lng, row.min_lat, row.max_lng, row.max_lat],
        )
        for row in results
    ]

    return ClustersResponse(clusters=clusters, points=[])


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    """Get full job detail by ID."""
    result = db.query(
        Job,
        func.ST_Y(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lat"),
        func.ST_X(func.ST_GeomFromWKB(func.ST_AsBinary(Job.geo))).label("lng"),
    ).options(joinedload(Job.company)).filter(Job.id == job_id).first()

    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    job, lat, lng = result
    return JobDetail(
        id=job.id,
        title=job.title,
        company=CompanyOut(
            id=job.company.id,
            name=job.company.name,
            website=job.company.website,
            logo_url=job.company.logo_url,
        ) if job.company else None,
        source=job.source,
        remote_type=job.remote_type,
        location_text=job.location_text,
        city=job.city,
        region=job.region,
        country=job.country,
        posted_at=job.posted_at,
        lat=lat,
        lng=lng,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        tags=job.tags,
        description_html=job.description_html,
        description_text=job.description_text,
        apply_url=job.apply_url,
        employment_type=job.employment_type,
        is_active=job.is_active,
    )
