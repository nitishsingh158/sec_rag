-- 1. Companies: one row per filer.
CREATE TABLE companies (
    cik     bigint PRIMARY KEY,        -- SEC id, e.g. 909832
    ticker  text   NOT NULL UNIQUE,
    name    text   NOT NULL            -- entityName from companyfacts
);

-- 2. Facts: every row from companyfacts, exactly as reported.
CREATE TABLE facts (
    id            bigserial PRIMARY KEY,
    cik           bigint  NOT NULL REFERENCES companies(cik),
    taxonomy      text    NOT NULL,    -- 'us-gaap', 'dei', ...
    tag           text    NOT NULL,
    unit          text    NOT NULL,    -- 'USD', 'shares', 'USD/shares'
    period_start  date,                -- NULL for point-in-time facts (balance sheet)
    period_end    date    NOT NULL,
    val           numeric NOT NULL,
    accn          text    NOT NULL,    -- filing accession number
    form          text    NOT NULL,    -- '10-K', '10-Q', ...
    filed         date    NOT NULL,
    fy            smallint,            -- fiscal year of the FILING, not of the value
    fp            text,                -- 'FY', 'Q1'..'Q3' of the filing
    frame         text,                -- calendar-aligned, kept but never used
    UNIQUE NULLS NOT DISTINCT (cik, taxonomy, tag, unit, period_start, period_end, accn)
);
CREATE INDEX facts_lookup ON facts (cik, tag, period_end);

-- 3. Metrics: the stable names the agent and verifier use.
CREATE TABLE metrics (
    metric       text PRIMARY KEY,     -- 'revenue', 'cost_of_sales', 'operating_cash_flow'
    description  text NOT NULL,
    period_type  text NOT NULL CHECK (period_type IN ('duration', 'instant'))
);

-- 4. Metric map: which tag means which metric, per company.
CREATE TABLE metric_map (
    cik         bigint   NOT NULL REFERENCES companies(cik),
    metric      text     NOT NULL REFERENCES metrics(metric),
    taxonomy    text     NOT NULL DEFAULT 'us-gaap',
    tag         text     NOT NULL,
    unit        text     NOT NULL DEFAULT 'USD',
    valid_from  date,                  -- NULL = no lower bound (tag switches over time)
    valid_to    date,                  -- NULL = no upper bound
    priority    smallint NOT NULL DEFAULT 1,   -- lowest wins if two tags cover a period
    PRIMARY KEY (cik, metric, taxonomy, tag, unit)
);
