# 🌍 JobMap

**Browse jobs on a 3D globe** — aggregates listings from 6 free job APIs and visualizes them on an interactive WebGL globe with filtering, search, and one-click apply.

![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+PostGIS-4169E1?logo=postgresql)
![License](https://img.shields.io/badge/License-MIT-green)

## Features

- 🌐 **Interactive 3D Globe** — explore jobs visually with globe.gl
- 🔍 **Smart Search** — full-text + company name + title matching
- 📍 **Country Navigation** — select a country, globe flies there
- 💼 **Work Type Filter** — remote, hybrid, on-site
- 🏛️ **Company Filter** — browse by company
- 🏷️ **Tech Tags** — filter by Python, React, AWS, etc.
- 📅 **Auto Scheduler** — ingests fresh jobs daily at 6 AM UTC
- 📄 **Rich Descriptions** — sanitized HTML rendering

## Quick Start

```bash
# Clone and configure
git clone https://github.com/<your-username>/jobmap.git
cd jobmap
cp .env.example .env

# Start everything
docker compose up --build

# In another terminal — ingest jobs from all 6 sources
curl -X POST "http://localhost:8000/api/admin/ingest?source=all" \
  -H "X-API-Key: dev-admin-key"
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Job Sources (all free, no API keys)

| Source | Type | Notable Companies |
|--------|------|------------------|
| Greenhouse | Mixed | Stripe, Figma, GitLab, Coinbase, Databricks |
| Ashby | Mixed | Ramp, Notion, Vercel, Linear, OpenAI |
| RemoteOK | Remote | Various |
| Arbeitnow | International | Europe-focused |
| Himalayas | Remote | Various |
| Jobicy | Remote | Various |

## Architecture

```
Frontend (Next.js) → FastAPI Backend → PostgreSQL + PostGIS
                                    ↕
                          6 Job Source APIs + Nominatim Geocoder
```

See [DOCS.md](DOCS.md) for the full architecture breakdown with diagrams.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, globe.gl, React Query, CSS |
| Backend | FastAPI, SQLAlchemy, APScheduler |
| Database | PostgreSQL + PostGIS |
| Geocoding | Nominatim (free) |
| Infra | Docker Compose |

## Deployment

- **Frontend** → Vercel (set root to `frontend`, add `NEXT_PUBLIC_API_BASE_URL`)
- **Backend** → Railway / Render / Fly.io (needs PostgreSQL + PostGIS)

## License

MIT
