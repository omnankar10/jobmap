"""Admin router for triggering ingestion."""
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.config import settings
from app.models.schemas import IngestionRunOut

router = APIRouter(tags=["admin"])

ALL_SOURCES = ["greenhouse", "remoteok", "arbeitnow", "himalayas", "jobicy", "ashby"]
SOURCE_PATTERN = f"^({'|'.join(ALL_SOURCES)}|all)$"


def verify_api_key(x_api_key: str = Header(...)):
    """Verify admin API key from header."""
    if x_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key


@router.post("/ingest", response_model=IngestionRunOut)
def trigger_ingestion(
    source: str = Query("greenhouse", pattern=SOURCE_PATTERN),
    api_key: str = Depends(verify_api_key),
    db: Session = Depends(get_db),
):
    """Trigger job ingestion from a source. Use source=all to ingest from all sources."""
    runs = []

    sources_to_run = [source] if source != "all" else ALL_SOURCES

    for src in sources_to_run:
        if src == "greenhouse":
            from app.ingestion.greenhouse import run_greenhouse_ingestion
            run = run_greenhouse_ingestion(db)
        elif src == "remoteok":
            from app.ingestion.remoteok import run_remoteok_ingestion
            run = run_remoteok_ingestion(db)
        elif src == "arbeitnow":
            from app.ingestion.arbeitnow import run_arbeitnow_ingestion
            run = run_arbeitnow_ingestion(db)
        elif src == "himalayas":
            from app.ingestion.himalayas import run_himalayas_ingestion
            run = run_himalayas_ingestion(db)
        elif src == "jobicy":
            from app.ingestion.jobicy import run_jobicy_ingestion
            run = run_jobicy_ingestion(db)
        elif src == "ashby":
            from app.ingestion.ashby import run_ashby_ingestion
            run = run_ashby_ingestion(db)
        else:
            raise HTTPException(status_code=400, detail=f"Source '{src}' not supported")
        runs.append(run)

    # Return the last run summary (or the only one)
    run = runs[-1]
    return IngestionRunOut(
        id=run.id,
        source=run.source if len(runs) == 1 else "all",
        started_at=run.started_at,
        ended_at=run.ended_at,
        status=run.status,
        jobs_fetched=sum(r.jobs_fetched for r in runs),
        jobs_inserted=sum(r.jobs_inserted for r in runs),
        jobs_updated=sum(r.jobs_updated for r in runs),
    )
