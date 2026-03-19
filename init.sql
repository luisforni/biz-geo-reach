CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS fetched_areas (
    id          BIGSERIAL PRIMARY KEY,
    bbox        GEOMETRY(POLYGON, 4326) NOT NULL,
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    categories  TEXT[] NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS fetched_areas_bbox_gist ON fetched_areas USING GIST (bbox);

CREATE TABLE IF NOT EXISTS commerce (
    id          BIGSERIAL PRIMARY KEY,
    osm_id      BIGINT UNIQUE NOT NULL,
    name        TEXT,
    category    TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    tags        JSONB,
    location    GEOMETRY(POINT, 4326) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS commerce_location_gist    ON commerce USING GIST (location);
CREATE INDEX IF NOT EXISTS commerce_category_idx     ON commerce (category);
CREATE INDEX IF NOT EXISTS commerce_subcategory_idx  ON commerce (subcategory);
CREATE INDEX IF NOT EXISTS commerce_name_trgm        ON commerce USING GIN (name gin_trgm_ops);
