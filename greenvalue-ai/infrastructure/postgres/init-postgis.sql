-- ============================================================
-- GreenValue AI - PostgreSQL + PostGIS Initialization
-- Runs on first container startup only
-- ============================================================

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for text search (address fuzzy matching)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify PostGIS installation
SELECT PostGIS_Version();

-- Log success
DO $$
BEGIN
    RAISE NOTICE 'GreenValue AI: PostGIS extensions initialized successfully';
END $$;
