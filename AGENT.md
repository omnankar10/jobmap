# Project Spec: “Mapertunity-like” Globe Job Browser (MVP → V1)
Owner: Om Nankar  
Goal: Build a web app that lets users browse job listings on an interactive **3D globe** (and optional 2D map), filter/search them, and open a job detail panel with an application link.  
Primary success metric: A user can land on the site, filter by role/location/remote, click pins, and reach “Apply” reliably.

---

## 0) Product Summary (What we’re building)
A web platform that displays job listings as points on a **globe visualization** and/or a **map visualization**, supporting:
- Keyword search (title/company/skills)
- Filters (remote type, location, tags, salary, recency)
- Fast performance with clustering/aggregation
- Reliable ingestion from structured job sources (start with **Greenhouse** + **Lever**)
- Clean geo handling (on-site pins, remote as separate UI)
- Public job detail pages for SEO (optional but recommended)

---

## 1) Core User Stories (MVP)
### 1.1 Anonymous Visitor
- Can open the site and see job points on a globe.
- Can zoom/rotate globe smoothly.
- Can search jobs using a keyword input (e.g., “data scientist”).
- Can filter by:
  - Remote type: `remote | hybrid | onsite`
  - Posted recency: `24h | 7d | 30d | all`
  - Salary min/max (if available)
  - Tags (e.g., “Python”, “SQL”, “Spark”, etc.)
  - Country/Region/City (if present)
- Can click a job point and open a **job detail drawer/panel**:
  - Title, company, location, remote type, posted date
  - Short description snippet
  - Apply button (external link)
- Can switch between:
  - **Globe view** (3D) and **Map view** (2D) (toggle recommended; not mandatory for MVP, but include in plan)

### 1.2 Admin (Internal Only)
- Can run ingestion manually and/or by schedule.
- Can see ingestion logs and counts.
- Can deduplicate jobs and flag bad entries (basic admin panel or CLI acceptable for MVP).

---

## 2) MVP Scope vs V1 vs V2
### MVP (Must Have)
- Globe visualization with points
- Filters + keyword search
- Job details panel + apply link
- Jobs ingestion from at least **1 structured source**
- Geocoding + normalized location
- Postgres database + basic API
- Clustering strategy OR server aggregation (must not crash browser with many points)

### V1 (Should Have)
- Both Greenhouse + Lever ingestion
- 2D map toggle
- Saved searches + alerts (email optional)
- Better deduping
- Basic admin UI (protected)

### V2 (Nice to Have)
- User accounts + candidate profiles
- Matching / recommendation (embeddings)
- Employer portal (post jobs directly)
- “Remote region overlays” (Remote-US, Remote-EMEA, etc.)
- Analytics (events, heatmaps)

---

## 3) Non-Functional Requirements
### Performance
- Must handle at least **50k job points** without locking up the UI.
- Use clustering/aggregation when zoomed out.
- Debounce filter/search queries.
- Cache results server-side and/or via CDN for common queries.

### Reliability
- Ingestion must be idempotent (re-running does not create duplicates).
- Apply links must be validated (non-empty URL).
- Geocoding must be cached to avoid repeated costs.

### Security
- Admin endpoints protected (API key / basic auth / OAuth later).
- Do not store user secrets in repo.
- Rate limit public API endpoints.

### Compliance
- Respect robots.txt and legal constraints for scraping.
- Prefer structured endpoints (Greenhouse/Lever) over brittle scraping.

---

## 4) High-Level Architecture
### Frontend (Web)
- Next.js (recommended)
- Globe visualization (WebGL):
  - Option A: `globe.gl` (Three.js based, fast, simpler)
  - Option B: Cesium (heavier, more complex)
- Optional 2D map:
  - Mapbox GL JS (recommended)
- UI: Tailwind + shadcn/ui
- Data fetching: React Query (recommended) or SWR
- Build public job pages:
  - `/job/[id]` for SEO and shareable links (recommended)

### Backend (API)
- FastAPI (Python) OR Node/Express (choose one; prefer FastAPI for data pipeline synergy)
- DB: PostgreSQL + PostGIS
- Search:
  - MVP: Postgres full-text search
  - V1+: Meilisearch / OpenSearch optional

### Ingestion / ETL
- Worker process (Python recommended)
- Scheduler:
  - MVP: cron / GitHub Actions / simple scheduled job
  - V1: Airflow/Prefect optional
- Geocoding:
  - Use Mapbox/Google/Nominatim (start with one)
  - Must cache geocode results by normalized location string

### Hosting
- Frontend: Vercel
- Backend: Render/Fly.io/AWS ECS
- Database: Neon/Supabase/RDS Postgres

---

## 5) Data Model (Postgres + PostGIS)
### 5.1 Tables
#### `companies`
- `id` UUID PK
- `name` TEXT UNIQUE
- `website` TEXT NULL
- `logo_url` TEXT NULL
- `industry` TEXT NULL
- `created_at` TIMESTAMP

Indexes:
- unique on `name`

#### `jobs`
- `id` UUID PK
- `source` TEXT NOT NULL  (e.g., `greenhouse`, `lever`, `manual`)
- `source_job_id` TEXT NOT NULL
- `company_id` UUID FK -> companies(id)
- `title` TEXT NOT NULL
- `description_html` TEXT NULL
- `description_text` TEXT NULL
- `apply_url` TEXT NOT NULL
- `employment_type` TEXT NULL (FT/PT/Contract/Intern)
- `remote_type` TEXT NOT NULL (`remote` | `hybrid` | `onsite`)
- `salary_min` INTEGER NULL
- `salary_max` INTEGER NULL
- `salary_currency` TEXT NULL (USD, etc.)
- `posted_at` TIMESTAMP NULL
- `scraped_at` TIMESTAMP NOT NULL
- `location_text` TEXT NULL (raw)
- `country` TEXT NULL
- `region` TEXT NULL (state/province)
- `city` TEXT NULL
- `geo` GEOGRAPHY(POINT, 4326) NULL (NULL for remote-without-specific city)
- `tags` TEXT[] NULL
- `is_active` BOOLEAN DEFAULT TRUE

Constraints:
- Unique composite: `(source, source_job_id)`
- `remote_type` must be one of allowed enum values

Indexes:
- `GIST(geo)` for geospatial queries
- `BTREE(posted_at)`
- `GIN(tags)`
- Full text index on `title + description_text + company name` (Postgres tsvector)

#### `geocode_cache`
- `id` UUID PK
- `query` TEXT UNIQUE (normalized location string)
- `city` TEXT NULL
- `region` TEXT NULL
- `country` TEXT NULL
- `lat` DOUBLE PRECISION NULL
- `lng` DOUBLE PRECISION NULL
- `geo` GEOGRAPHY(POINT, 4326) NULL
- `raw_response` JSONB NULL
- `created_at` TIMESTAMP

#### `ingestion_runs`
- `id` UUID PK
- `source` TEXT
- `started_at` TIMESTAMP
- `ended_at` TIMESTAMP
- `status` TEXT (`success` | `failed`)
- `jobs_fetched` INT
- `jobs_inserted` INT
- `jobs_updated` INT
- `errors` JSONB NULL

---

## 6) Backend API Spec (MVP)
Base URL: `/api`

### 6.1 List Jobs (for map/globe)
`GET /api/jobs`
Query params:
- `q`: string (keyword)
- `remote_type`: `remote|hybrid|onsite|any`
- `posted_since`: `24h|7d|30d|all`
- `salary_min`: int
- `salary_max`: int
- `tags`: comma-separated list
- `country`, `region`, `city`: optional filters
- `bbox`: `minLng,minLat,maxLng,maxLat` (for 2D map viewport fetch)
- `zoom`: number (optional; used for server-side clustering logic)
- `limit`, `offset`

Response (MVP minimal):
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Data Scientist",
      "company": {"id":"uuid","name":"Acme"},
      "remote_type": "onsite",
      "location_text": "Austin, TX",
      "posted_at": "2026-02-20T00:00:00Z",
      "lat": 30.2672,
      "lng": -97.7431,
      "salary_min": 120000,
      "salary_max": 160000,
      "tags": ["python","sql"]
    }
  ],
  "meta": {"total": 12345}
}