"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import jobs, admin
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle — starts the scheduler on boot."""
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="JobMap API",
    description="Browse job listings on a 3D globe",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/health")
def health():
    return {"status": "ok"}
