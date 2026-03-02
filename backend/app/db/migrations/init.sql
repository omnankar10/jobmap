-- JobMap Database Schema (Postgres + PostGIS)
-- Run: psql -d jobmap -f init.sql

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================
-- Companies
-- ============================
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL,
    website TEXT,
    logo_url TEXT,
    industry TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================
-- Jobs
-- ============================
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    source_job_id TEXT NOT NULL,
    company_id UUID REFERENCES companies(id),
    title TEXT NOT NULL,
    description_html TEXT,
    description_text TEXT,
    apply_url TEXT NOT NULL,
    employment_type TEXT,
    remote_type TEXT NOT NULL DEFAULT 'onsite'
        CHECK (remote_type IN ('remote', 'hybrid', 'onsite')),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT,
    posted_at TIMESTAMP,
    scraped_at TIMESTAMP NOT NULL DEFAULT NOW(),
    location_text TEXT,
    country TEXT,
    region TEXT,
    city TEXT,
    geo GEOGRAPHY(POINT, 4326),
    tags TEXT[],
    is_active BOOLEAN DEFAULT TRUE,

    CONSTRAINT uq_source_job UNIQUE (source, source_job_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS ix_jobs_geo ON jobs USING GIST (geo);
CREATE INDEX IF NOT EXISTS ix_jobs_posted_at ON jobs USING BTREE (posted_at);
CREATE INDEX IF NOT EXISTS ix_jobs_tags ON jobs USING GIN (tags);

-- Full-text search index
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE OR REPLACE FUNCTION jobs_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector :=
        setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.description_text, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS jobs_search_vector_trigger ON jobs;
CREATE TRIGGER jobs_search_vector_trigger
    BEFORE INSERT OR UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION jobs_search_vector_update();

CREATE INDEX IF NOT EXISTS ix_jobs_search ON jobs USING GIN (search_vector);

-- ============================
-- Geocode Cache
-- ============================
CREATE TABLE IF NOT EXISTS geocode_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query TEXT UNIQUE NOT NULL,
    city TEXT,
    region TEXT,
    country TEXT,
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    geo GEOGRAPHY(POINT, 4326),
    raw_response JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================
-- Ingestion Runs
-- ============================
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source TEXT NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    status TEXT DEFAULT 'running',
    jobs_fetched INTEGER DEFAULT 0,
    jobs_inserted INTEGER DEFAULT 0,
    jobs_updated INTEGER DEFAULT 0,
    errors JSONB
);
