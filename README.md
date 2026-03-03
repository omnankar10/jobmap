# 🌍 JobMap

**Browse jobs on a 3D globe** — aggregates listings from 6 free job APIs and visualizes them on an interactive WebGL globe with filtering, search, and one-click apply.

🔗 **Live App**: [jobmap-steel.vercel.app](https://jobmap-steel.vercel.app)

![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+PostGIS-4169E1?logo=postgresql)
![Railway](https://img.shields.io/badge/Deployed-Railway-0B0D0E?logo=railway)
![Vercel](https://img.shields.io/badge/Frontend-Vercel-000?logo=vercel)

## Features

- 🌐 **Interactive 3D Globe** — explore jobs visually with globe.gl
- 📊 **Table View** — toggle between globe and table with one click
- 🔍 **Smart Search** — full-text + company name + title matching
- 📍 **Country Navigation** — select a country, globe flies there
- 💼 **Work Type Filter** — remote, hybrid, on-site
- 🏛️ **Company Filter** — browse by company
- 🏷️ **Tech Tags** — filter by Python, React, AWS, etc.
- 📅 **Auto Scheduler** — ingests fresh jobs daily at 6 AM UTC
- 🗺️ **Mapbox Geocoding** — precise lat/lng with caching layer
- 📄 **Rich Descriptions** — sanitized HTML rendering

## Architecture

```
Next.js Frontend (Vercel) → REST API → FastAPI Backend (Railway) → PostgreSQL 15 + PostGIS (Railway)
                                                                 → Mapbox Geocoding API
                                                                 → 6 External Job APIs
```

## Job Sources (all free, no API keys needed)

| Source | Type | Notable Companies |
|--------|------|------------------|
| Greenhouse | Mixed | Stripe, Figma, GitLab, Coinbase, Databricks |
| Ashby | Mixed | Ramp, Notion, Vercel, Linear, OpenAI |
| RemoteOK | Remote | Various |
| Arbeitnow | International | Europe-focused |
| Himalayas | Remote | Various |
| Jobicy | Remote | Various |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, globe.gl, React Query, CSS |
| Backend | FastAPI, SQLAlchemy, APScheduler |
| Database | PostgreSQL 15 + PostGIS |
| Geocoding | Mapbox API + Nominatim (fallback) |
| Search | tsvector + GIN index (full-text) |
| Spatial | PostGIS geography + GIST index |
| Deployment | Vercel (frontend), Railway (backend + DB) |

## Local Development

```bash
# Clone and configure
git clone https://github.com/omnankar10/jobmap.git
cd jobmap
cp .env.example .env

# Start everything with Docker
docker compose up --build

# Ingest jobs from all 6 sources
curl -X POST "http://localhost:8000/api/admin/ingest?source=all" \
  -H "X-API-Key: dev-admin-key"
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Geocoding Backfill

For jobs with missing geo data, run the Mapbox backfill:

```bash
export DATABASE_URL="postgresql://..."
export MAPBOX_TOKEN="pk...."
python3 backend/scripts/backfill_geo_mapbox.py
```

## Deployment

| Service | Platform | Config |
|---------|----------|--------|
| Frontend | **Vercel** | Root: `frontend`, Framework: Next.js, Env: `NEXT_PUBLIC_API_BASE_URL` |
| Backend | **Railway** | Root: `backend`, Dockerfile deploy, Env: `DATABASE_URL`, `ADMIN_API_KEY`, `CORS_ORIGINS` |
| Database | **Railway** | PostgreSQL addon with PostGIS extension enabled |

## Documentation

See [DOCS.md](DOCS.md) for the full architecture breakdown, component details, flow diagrams, and API reference.

## License

MIT
