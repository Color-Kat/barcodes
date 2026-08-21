-- Barcode product database — Layer 1 (identity) + Layer 2 (enrichment) scaffolding.
-- Applied idempotently by db.py init.

CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- fuzzy name matching for barcode-less sources

-- raw_items: one row per (source, source_id) exactly as fetched. Re-running a
-- source UPSERTs here — this is the actualization log and the audit trail. The
-- full original payload is kept in `raw` so a parser fix can re-derive fields
-- offline without re-hitting the network.
CREATE TABLE IF NOT EXISTS raw_items (
    source      TEXT NOT NULL,
    source_id   TEXT NOT NULL,
    barcode     TEXT,                      -- normalized EAN-13/8, or NULL if source has none
    name        TEXT,
    brand       TEXT,
    ingredients TEXT,
    kcal        REAL, protein REAL, fat REAL, carbs REAL,
    weight      TEXT,
    photo       TEXT,
    raw         JSONB,                      -- everything else, verbatim
    fetched_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_raw_barcode ON raw_items (barcode) WHERE barcode IS NOT NULL;
-- trigram index on normalized name powers enrich-by-name for sources without EAN
CREATE INDEX IF NOT EXISTS idx_raw_name_trgm ON raw_items USING gin (name gin_trgm_ops);

-- products: merged view keyed by barcode. Rebuilt from raw_items by merge().
-- This is what the app queries at runtime (Layer 1 answer: barcode -> name+…).
CREATE TABLE IF NOT EXISTS products (
    barcode     TEXT PRIMARY KEY,
    name        TEXT,
    brand       TEXT,
    ingredients TEXT,
    kcal        REAL, protein REAL, fat REAL, carbs REAL,
    weight      TEXT,
    photo       TEXT,
    country     TEXT,                       -- GS1-prefix country (issuing org)
    extra       JSONB,
    sources     TEXT[],                      -- contributing source names
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_name_trgm ON products USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_products_has_kbju ON products (barcode) WHERE kcal IS NOT NULL;
