# JobMap — Project Documentation

> **A 3D globe-based job browser** that aggregates listings from 6 free job APIs and visualizes them on an interactive WebGL globe. Filter by country, company, work type, recency, and skills — then click any point to see the full listing.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Data Flow](#data-flow)
4. [Backend](#backend)
5. [Frontend](#frontend)
6. [Ingestion Pipeline](#ingestion-pipeline)
7. [Scheduler](#scheduler)
8. [Database](#database)
9. [Project Structure](#project-structure)
10. [Deployment](#deployment)
11. [Environment Variables](#environment-variables)

---

## Overview

JobMap solves the problem of fragmented job boards by **aggregating jobs from multiple sources** and displaying them on a 3D globe. Users can:

- 🌍 Explore jobs on an interactive 3D globe
- 🔍 Search by job title, company name, or keywords
- 📍 Filter by country (globe auto-navigates to it)
- 🏛️ Filter by company
- 💼 Filter by work type (remote / hybrid / on-site)
- 🕐 Filter by recency (24h, 7d, 30d)
- 🏷️ Filter by technology tags
- 📄 View full HTML job descriptions and apply directly

---

## Architecture

```mermaid
graph TB
    subgraph "Frontend - Next.js"
        A["page.tsx - Main App"]
        B["Globe.tsx - 3D WebGL Globe"]
        C["FilterPanel.tsx - Sidebar Filters"]
        D["JobDrawer.tsx - Job Detail Drawer"]
        E["Tooltip.tsx - Hover Tooltip"]
    end

    subgraph "Backend - FastAPI"
        F["main.py - App Entry + Scheduler"]
        G["jobs.py Router"]
        H["admin.py Router"]
        I["scheduler.py - APScheduler Cron"]
    end

    subgraph "Ingestion Layer"
        J["greenhouse.py"]
        K["remoteok.py"]
        L["arbeitnow.py"]
        M["himalayas.py"]
        N["jobicy.py"]
        O["ashby.py"]
    end

    subgraph "Services"
        P["geocoder.py"]
        Q["location_parser.py"]
    end

    subgraph "Database"
        R["PostgreSQL + PostGIS"]
    end

    subgraph "External APIs"
        S["Greenhouse"]
        T["RemoteOK"]
        U["Arbeitnow"]
        V["Himalayas"]
        W["Jobicy"]
        X["Ashby"]
        Y["Nominatim Geocoder"]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    A -->|"fetch /api/jobs"| G
    A -->|"fetch /api/companies"| G
    A -->|"fetch /api/countries"| G
    C -->|"onCountrySelect"| B

    G --> R
    H -->|"POST /ingest"| J & K & L & M & N & O
    I -->|"daily cron"| J & K & L & M & N & O

    J --> S
    K --> T
    L --> U
    M --> V
    N --> W
    O --> X

    J & K & L & M & N & O --> P
    P --> Y
    P --> Q
    P --> R
```

---

## Data Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant DB
    participant Sources

    Note over API,Sources: Ingestion (daily or manual)
    API->>Sources: Fetch jobs from 6 APIs
    Sources-->>API: Raw job data (JSON)
    API->>API: Parse, tag, geocode
    API->>DB: Upsert jobs + companies

    Note over User,DB: User browsing
    User->>Frontend: Opens app
    Frontend->>API: GET /api/jobs?filters
    API->>DB: Query with filters
    DB-->>API: Job results
    API-->>Frontend: JSON response
    Frontend->>Frontend: Render on globe

    User->>Frontend: Clicks point on globe
    Frontend->>API: GET /api/jobs/{id}
    API->>DB: Fetch full detail
    DB-->>API: Job detail + HTML
    API-->>Frontend: Full job data
    Frontend->>Frontend: Show drawer with description

    User->>Frontend: Selects country filter
    Frontend->>Frontend: Globe flies to country
    Frontend->>API: GET /api/jobs?country=X
    API-->>Frontend: Filtered results
```

---

## Backend

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Framework | **FastAPI** (Python 3.11) |
| ORM | **SQLAlchemy 2.0** + GeoAlchemy2 |
| Database | **PostgreSQL 15** + PostGIS |
| Migrations | Alembic |
| HTTP Client | httpx |
| Geocoding | geopy (Nominatim) |
| Scheduler | APScheduler |
| Server | Uvicorn |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/jobs` | List jobs with filters (q, remote_type, posted_since, tags, country, company_id, bbox) |
| `GET` | `/api/jobs/{id}` | Full job detail including HTML description |
| `GET` | `/api/jobs/clusters` | Server-side clustered data for zoomed-out globe |
| `GET` | `/api/companies` | All companies with job counts |
| `GET` | `/api/countries` | All countries with job counts |
| `POST` | `/api/admin/ingest?source=all` | Trigger ingestion (requires `X-API-Key` header) |
| `GET` | `/health` | Health check |

### Key Components

#### `main.py` — Application Entry
- Creates the FastAPI app with CORS middleware
- Registers routers (`/api` for jobs, `/api/admin` for admin)
- Uses `lifespan` context manager to start/stop the scheduler

#### `routers/jobs.py` — Job Endpoints
- Full-text search with `search_vector @@ plainto_tsquery` + company name ILIKE + title ILIKE
- Geospatial filtering with `ST_MakeEnvelope` and `ST_Intersects`
- Server-side clustering with `ST_SnapToGrid` for the globe
- Pagination with `limit`/`offset`

#### `routers/admin.py` — Admin Endpoints
- API key authentication via `X-API-Key` header
- Supports all 6 sources individually or `source=all`

#### `services/geocoder.py` — Geocoding Service
- Uses Nominatim (free, no API key) to convert location strings to lat/lng
- Caches geocoding results in the `geocache` table to avoid rate limits
- Falls back gracefully when geocoding fails

#### `services/location_parser.py` — Location Parser
- Extracts remote type (remote/hybrid/onsite) from location strings
- Normalizes location text for consistent geocoding
- Detects country hints from text like "Remote (US)"

---

## Frontend

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Framework | **Next.js 16** (App Router) |
| 3D Globe | **globe.gl** + Three.js |
| State | React Query (`@tanstack/react-query`) |
| Styling | **Vanilla CSS** (dark theme, glassmorphism) |
| Fonts | Inter (Google Fonts) |

### Components

#### `page.tsx` — Main App Page
- Manages all state: filters, selected job, hovered job, drawer visibility
- Holds a `ref` to the Globe for programmatic `flyTo()` navigation
- Contains a built-in **35-country coordinate lookup** for globe navigation
- Wires FilterPanel → API → Globe → JobDrawer

#### `Globe.tsx` — 3D WebGL Globe
- Renders Earth with blue marble texture, bump map, and atmosphere
- Displays job points colored by work type (purple=remote, teal=hybrid, red=onsite, gold=selected)
- Auto-rotates slowly, **pauses on user interaction**, resumes after 5s idle
- Exposes `flyTo(lat, lng, altitude)` via `forwardRef` + `useImperativeHandle`
- Dynamic import (`next/dynamic`) to avoid SSR issues with WebGL

#### `FilterPanel.tsx` — Sidebar Filters
- **Search** — debounced 300ms, queries title + company + full-text
- **Country** — dropdown from `/api/countries`, triggers globe navigation
- **Company** — dropdown from `/api/companies` with job counts
- **Work Type** — pill buttons (All / On-site / Hybrid / Remote)
- **Recency** — 4-column grid (Any / 24h / 7d / 30d)
- **Tags** — 18 popular technology tags as toggle chips
- **Reset** — clears all filters and resets globe position

#### `JobDrawer.tsx` — Job Detail Slide-in Panel
- Fetches full job detail lazily via React Query
- Sanitizes HTML descriptions (strips scripts, event handlers, inline styles)
- Falls back: `description_html` → detects HTML in `description_text` → plain text
- Displays salary, badges, tags, post date, and a prominent "Apply Now" button

#### `Tooltip.tsx` — Globe Hover Tooltip
- Shows job title, company, and location on point hover

### Styling (`globals.css`)
- **Dark theme** with CSS custom properties
- **Glassmorphism** effects (backdrop-filter, translucent backgrounds)
- **Micro-animations** (fadeIn, shimmer loading skeletons, hover transforms)
- Custom scrollbar, premium typography, responsive layout

---

## Ingestion Pipeline

Six connectors, all using **free APIs with no authentication required**:

| Source | API Endpoint | Jobs Type | Special Features |
|--------|-------------|-----------|-----------------|
| **Greenhouse** | `boards-api.greenhouse.io/v1/boards/{name}/jobs` | Mixed (10 boards: Stripe, Figma, GitLab, Coinbase, Databricks, Notion, Shopify, Twilio, Cloudflare, HashiCorp) | Company-specific boards |
| **RemoteOK** | `remoteok.com/api` | Remote only | Source tags included |
| **Arbeitnow** | `arbeitnow.com/api/job-board-api` | International (Europe-heavy) | Paginated, remote flag |
| **Himalayas** | `himalayas.app/jobs/api` | Remote only | Salary data, location restrictions |
| **Jobicy** | `jobicy.com/api/v2/remote-jobs` | Remote only | Geographic data, industry tags |
| **Ashby** | `api.ashbyhq.com/posting-api/job-board/{name}` | Mixed (8 boards: Ramp, Notion, Vercel, Linear, Mercury, OpenAI, Retool, Plaid) | Compensation data |

### Ingestion Process (per source)

```mermaid
flowchart LR
    A["Fetch from API"] --> B["Parse & extract fields"]
    B --> C["Extract tags via keywords"]
    C --> D["Get/create company"]
    D --> E["Upsert job record"]
    E --> F["Geocode location"]
    F --> G["Commit to DB"]
```

Each connector:
1. Fetches raw JSON
2. Extracts fields (title, description, salary, location, etc.)
3. Tags jobs using keyword matching against 25+ tech terms
4. Creates company records if they don't exist
5. Upserts jobs (insert new, update existing by `source + source_job_id`)
6. Geocodes location text → lat/lng via Nominatim
7. Logs results to `ingestion_runs` table

---

## Scheduler

The scheduler is powered by **APScheduler** and runs inside the FastAPI process:

```mermaid
flowchart TD
    A["FastAPI Startup"] --> B["start_scheduler()"]
    B --> C["CronTrigger: hour=SCHEDULER_HOUR"]
    C --> D["run_all_ingestion()"]
    D --> E["greenhouse.py"]
    D --> F["remoteok.py"]
    D --> G["arbeitnow.py"]
    D --> H["himalayas.py"]
    D --> I["jobicy.py"]
    D --> J["ashby.py"]
    E & F & G & H & I & J --> K["Log results"]
    A --> L["FastAPI Shutdown"]
    L --> M["stop_scheduler()"]
```

- **Default schedule**: Daily at 6:00 AM UTC
- **Configurable**: Set `SCHEDULER_HOUR` (0–23) in `.env`
- **Disable**: Set `SCHEDULER_ENABLED=false`
- Each source runs in a try/except — one failure doesn't stop others

---

## Database

### Schema (PostgreSQL + PostGIS)

```mermaid
erDiagram
    COMPANIES {
        uuid id PK
        string name UK
        string website
        string logo_url
        timestamp created_at
    }

    JOBS {
        uuid id PK
        string source
        string source_job_id
        uuid company_id FK
        string title
        text description_html
        text description_text
        string apply_url
        string remote_type
        string employment_type
        string location_text
        string city
        string region
        string country
        geography geo
        integer salary_min
        integer salary_max
        string salary_currency
        string_array tags
        tsvector search_vector
        timestamp posted_at
        timestamp scraped_at
        boolean is_active
    }

    GEOCACHE {
        uuid id PK
        string query_text UK
        float lat
        float lng
        string city
        string region
        string country
    }

    INGESTION_RUNS {
        uuid id PK
        string source
        timestamp started_at
        timestamp ended_at
        string status
        integer jobs_fetched
        integer jobs_inserted
        integer jobs_updated
        json errors
    }

    COMPANIES ||--o{ JOBS : "has many"
```

### Key Indexes
- `search_vector` — GIN index for full-text search
- `geo` — GIST index for geospatial queries
- `(source, source_job_id)` — unique constraint for upserts

---

## Project Structure

```
jobmap/
├── docker-compose.yml          # PostgreSQL + PostGIS, backend, frontend
├── .env.example                # Environment variable template
├── .gitignore
├── README.md                   # Quick start guide
├── DOCS.md                     # This file
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt        # Python dependencies
│   └── app/
│       ├── main.py             # FastAPI app + lifespan hooks
│       ├── config.py           # Pydantic settings from .env
│       ├── scheduler.py        # APScheduler daily cron
│       ├── db/
│       │   ├── database.py     # SQLAlchemy engine + session
│       │   └── init.sql        # PostGIS + table DDL + indexes
│       ├── models/
│       │   ├── models.py       # SQLAlchemy ORM models
│       │   └── schemas.py      # Pydantic response schemas
│       ├── routers/
│       │   ├── jobs.py         # /api/jobs, /api/companies, /api/countries
│       │   └── admin.py        # /api/admin/ingest
│       ├── services/
│       │   ├── geocoder.py     # Nominatim geocoding + cache
│       │   └── location_parser.py  # Location text normalization
│       └── ingestion/
│           ├── greenhouse.py   # Greenhouse boards connector
│           ├── remoteok.py     # RemoteOK connector
│           ├── arbeitnow.py    # Arbeitnow connector
│           ├── himalayas.py    # Himalayas connector
│           ├── jobicy.py       # Jobicy connector
│           ├── ashby.py        # Ashby boards connector
│           └── seed.py         # Initial seed data
│
└── frontend/
    ├── Dockerfile
    ├── .dockerignore
    ├── package.json
    ├── next.config.ts
    ├── tsconfig.json
    └── src/
        ├── app/
        │   ├── layout.tsx      # Root layout (Inter font, React Query)
        │   ├── page.tsx        # Main app (globe + filters + drawer)
        │   ├── globals.css     # Full dark theme CSS
        │   └── job/[id]/page.tsx  # SSR job detail (SEO + OG tags)
        ├── components/
        │   ├── Globe.tsx       # 3D globe (globe.gl + forwardRef)
        │   ├── FilterPanel.tsx # Sidebar filters + country navigation
        │   ├── JobDrawer.tsx   # Job detail slide-in drawer
        │   └── Tooltip.tsx     # Hover tooltip
        └── lib/
            ├── api.ts          # API client functions
            ├── types.ts        # TypeScript interfaces
            └── providers.tsx   # React Query provider
```

---

## Deployment

### Local Development (Docker)
```bash
cp .env.example .env
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Ingest:   curl -X POST "http://localhost:8000/api/admin/ingest?source=all" -H "X-API-Key: dev-admin-key"
```

### Vercel (Frontend)
1. Push to GitHub
2. Import repo in Vercel
3. Set **Root Directory** to `frontend`
4. Set **Framework Preset** to Next.js
5. Add environment variable: `NEXT_PUBLIC_API_BASE_URL` = your backend URL
6. Deploy

### Backend (Railway / Render / Fly.io)
The backend + PostgreSQL needs a server runtime. Options:
- **Railway**: Add PostgreSQL add-on, deploy backend from `backend/` directory
- **Render**: Create a Web Service + PostgreSQL database
- **Fly.io**: Deploy with `fly launch` from `backend/`

Set `DATABASE_URL`, `ADMIN_API_KEY`, `CORS_ORIGINS` in the deployment environment.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://jobmap:jobmap@localhost:5432/jobmap` | PostgreSQL connection string |
| `ADMIN_API_KEY` | `dev-admin-key` | API key for admin/ingest endpoints |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated) |
| `GEOCODER_PROVIDER` | `nominatim` | Geocoding provider |
| `SCHEDULER_ENABLED` | `true` | Enable/disable daily scheduler |
| `SCHEDULER_HOUR` | `6` | UTC hour for daily ingestion (0–23) |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend URL for frontend |
