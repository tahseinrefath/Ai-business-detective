-- AI Business Detective - PostgreSQL schema (optional mirror; the app also works with file storage)
CREATE TABLE IF NOT EXISTS datasets (
    id          SERIAL PRIMARY KEY,
    filename    TEXT        NOT NULL,
    upload_date TIMESTAMP   NOT NULL DEFAULT NOW(),
    row_count   INTEGER     NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id           BIGSERIAL PRIMARY KEY,
    dataset_id   INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    order_date   DATE    NOT NULL,
    product      TEXT,
    category     TEXT,
    region       TEXT,
    quantity     INTEGER,
    sales        NUMERIC(14,2) NOT NULL,
    profit       NUMERIC(14,2),            -- NULL = unknown, never silently 0
    discount_pct NUMERIC(5,2)
);
CREATE INDEX IF NOT EXISTS idx_sales_dataset_date ON sales (dataset_id, order_date);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id            SERIAL PRIMARY KEY,
    dataset_id    INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    analysis_date TIMESTAMP NOT NULL DEFAULT NOW(),
    status        TEXT NOT NULL DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS insights (
    id          SERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    finding     TEXT NOT NULL,
    evidence    TEXT NOT NULL,
    severity    TEXT CHECK (severity IN ('low','medium','high'))
);

CREATE TABLE IF NOT EXISTS reports (
    id          SERIAL PRIMARY KEY,
    analysis_id INTEGER NOT NULL REFERENCES analysis_runs(id) ON DELETE CASCADE,
    report_path TEXT NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
