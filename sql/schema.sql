-- =============================================================================
-- schema.sql — Customer Revenue Intelligence (SYNTHETIC DATA)
-- =============================================================================
-- Design: Option B — normalised relational model (3NF) + flat analytical views.
--
--   TRANSACTIONAL CORE (Steps 2-3)
--   locations 1 ──< customers 1 ──< orders 1 ──< order_items >── 1 products
--
--   ANALYTICS LAYER (Step 10 - outputs of the Python steps, keyed on customer_id / month)
--   customers 1 ──1 customer_rfm      >── 1 rfm_segment_definitions   (Step 5, rule-based RFM)
--   customers 1 ──1 customer_segments >── 1 ml_clusters               (Step 6, K-Means)
--   customers 1 ──1 customer_value                                    (Step 7, CLV)
--   revenue_forecasts (month x record_type)                           (Step 9, time-series forecast)
--
-- * Analytics tables store only what the Python steps PRODUCED (scores, labels, estimates). Anything that can be
--   recomputed from the transactional tables (quantities, AOV, totals) is computed in SQL, not duplicated.
--
-- * The raw CSV is ONE denormalised table (one row per order line). After
--   cleaning (Step 3) it is split into these five tables.
-- * vw_sales_flat re-joins them into the original 23-column layout, so Python,
--   Power BI and Streamlit can read one familiar shape while SQL analysis
--   benefits from keys, constraints and joins.
-- * Dialect: SQLite 3 (runs with Python's built-in sqlite3). PostgreSQL notes
--   are given in comments where syntax differs.
-- * Load CLEANED data only: the CHECK constraints deliberately reject the
--   raw data-quality issues (negative quantities, 15 instead of 0.15, etc.).
-- =============================================================================

PRAGMA foreign_keys = ON;   -- SQLite enforces FKs only when this is on

DROP VIEW  IF EXISTS vw_delivered_sales;
DROP VIEW  IF EXISTS vw_sales_flat;
DROP TABLE IF EXISTS revenue_forecasts;
DROP TABLE IF EXISTS customer_value;
DROP TABLE IF EXISTS customer_segments;
DROP TABLE IF EXISTS ml_clusters;
DROP TABLE IF EXISTS customer_rfm;
DROP TABLE IF EXISTS rfm_segment_definitions;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS locations;

-- -----------------------------------------------------------------------------
-- 1. locations — geography hierarchy (City -> State -> Region)
-- -----------------------------------------------------------------------------
CREATE TABLE locations (
    location_id   INTEGER PRIMARY KEY,          -- PostgreSQL: SERIAL / IDENTITY
    city          TEXT    NOT NULL,
    state         TEXT    NOT NULL,
    region        TEXT    NOT NULL
                  CHECK (region IN ('North', 'South', 'East', 'West', 'Central')),
    UNIQUE (city, state)
);

-- -----------------------------------------------------------------------------
-- 2. customers — one row per customer (attributes constant over the period)
-- -----------------------------------------------------------------------------
CREATE TABLE customers (
    customer_id    TEXT    PRIMARY KEY,         -- e.g. CUST-0001
    customer_name  TEXT    NOT NULL,
    customer_age   INTEGER CHECK (customer_age BETWEEN 18 AND 100),  -- NULL allowed if unknown
    gender         TEXT    CHECK (gender IN ('Male', 'Female', 'Other', 'Unknown')),  -- 'Unknown' = not recoverable in cleaning
    location_id    INTEGER NOT NULL REFERENCES locations (location_id)
);

-- -----------------------------------------------------------------------------
-- 3. products — product master
-- -----------------------------------------------------------------------------
CREATE TABLE products (
    product_id     TEXT PRIMARY KEY,            -- e.g. ELE-001
    product_name   TEXT NOT NULL UNIQUE,
    category       TEXT NOT NULL
                   CHECK (category IN ('Electronics', 'Fashion', 'Home & Kitchen',
                                       'Beauty', 'Sports', 'Books')),
    sub_category   TEXT NOT NULL
);

-- -----------------------------------------------------------------------------
-- 4. orders — order header (one row per checkout)
-- -----------------------------------------------------------------------------
CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,           -- e.g. ORD-000001
    customer_id     TEXT NOT NULL REFERENCES customers (customer_id),
    order_date      DATE NOT NULL,              -- stored as ISO text 'YYYY-MM-DD' in SQLite
    payment_method  TEXT NOT NULL
                    CHECK (payment_method IN ('UPI', 'Card', 'COD', 'Net Banking',
                                              'Wallet', 'Unknown')),
    customer_type   TEXT NOT NULL CHECK (customer_type IN ('New', 'Returning'))
);

-- -----------------------------------------------------------------------------
-- 5. order_items — order lines (the grain of the fact data)
-- -----------------------------------------------------------------------------
CREATE TABLE order_items (
    order_line_id  TEXT    PRIMARY KEY,         -- e.g. OL-0000001
    order_id       TEXT    NOT NULL REFERENCES orders (order_id),
    product_id     TEXT    NOT NULL REFERENCES products (product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     REAL    NOT NULL CHECK (unit_price > 0),   -- price at time of sale
    discount       REAL    NOT NULL CHECK (discount BETWEEN 0 AND 0.40),
    sales          REAL    NOT NULL CHECK (sales >= 0),       -- PostgreSQL: NUMERIC(12,2)
    cost           REAL    NOT NULL CHECK (cost >= 0),
    profit         REAL    NOT NULL,                          -- may be negative
    order_status   TEXT    NOT NULL
                   CHECK (order_status IN ('Delivered', 'Cancelled', 'Returned')),
    -- business-rule constraints (1 rupee rounding tolerance)
    CHECK (ABS(sales  - quantity * unit_price * (1 - discount)) <= 1.0),
    CHECK (ABS(profit - (sales - cost)) <= 1.0)
);

-- -----------------------------------------------------------------------------
-- Indexes for the joins and filters used most in analysis
-- -----------------------------------------------------------------------------
CREATE INDEX idx_customers_location  ON customers   (location_id);
CREATE INDEX idx_orders_customer     ON orders      (customer_id);
CREATE INDEX idx_orders_date         ON orders      (order_date);
CREATE INDEX idx_items_order         ON order_items (order_id);
CREATE INDEX idx_items_product       ON order_items (product_id);
CREATE INDEX idx_items_status        ON order_items (order_status);

-- -----------------------------------------------------------------------------
-- vw_sales_flat — the analysis-ready, one-row-per-order-line view
-- (same 23 columns as the source CSV)
-- -----------------------------------------------------------------------------
CREATE VIEW vw_sales_flat AS
SELECT
    oi.order_line_id  AS Order_Line_ID,
    o.order_id        AS Order_ID,
    o.order_date      AS Order_Date,
    c.customer_id     AS Customer_ID,
    c.customer_name   AS Customer_Name,
    c.customer_age    AS Customer_Age,
    c.gender          AS Gender,
    l.city            AS City,
    l.state           AS State,
    l.region          AS Region,
    p.product_id      AS Product_ID,
    p.product_name    AS Product_Name,
    p.category        AS Category,
    p.sub_category    AS Sub_Category,
    oi.quantity       AS Quantity,
    oi.unit_price     AS Unit_Price,
    oi.discount       AS Discount,
    oi.sales          AS Sales,
    oi.cost           AS Cost,
    oi.profit         AS Profit,
    o.payment_method  AS Payment_Method,
    oi.order_status   AS Order_Status,
    o.customer_type   AS Customer_Type
FROM order_items oi
JOIN orders    o ON o.order_id    = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
JOIN locations l ON l.location_id = c.location_id
JOIN products  p ON p.product_id  = oi.product_id;


-- =============================================================================
-- ANALYTICS LAYER (Step 10)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 6. rfm_segment_definitions — the 11 rule-based RFM segments of Step 5
-- -----------------------------------------------------------------------------
CREATE TABLE rfm_segment_definitions (
    segment_name          TEXT    PRIMARY KEY,
    priority              INTEGER NOT NULL UNIQUE CHECK (priority BETWEEN 1 AND 11),  -- first matching rule wins
    rule_text             TEXT    NOT NULL,
    business_meaning      TEXT    NOT NULL,
    value_activity_group  TEXT    NOT NULL
                          CHECK (value_activity_group IN ('Active high value', 'Developing', 'Slipping', 'Inactive'))
);

-- -----------------------------------------------------------------------------
-- 7. customer_rfm — Step 5 RFM values and scores (one row per customer with >= 1 Delivered order)
-- -----------------------------------------------------------------------------
CREATE TABLE customer_rfm (
    customer_id          TEXT    PRIMARY KEY REFERENCES customers (customer_id),
    reference_date       DATE    NOT NULL,                      -- 2026-01-01 = last order date + 1 day
    recency_days         INTEGER NOT NULL CHECK (recency_days >= 1),
    frequency_orders     INTEGER NOT NULL CHECK (frequency_orders >= 1),
    monetary_revenue     REAL    NOT NULL CHECK (monetary_revenue > 0),
    r_score              INTEGER NOT NULL CHECK (r_score BETWEEN 1 AND 5),
    f_score              INTEGER NOT NULL CHECK (f_score BETWEEN 1 AND 5),
    m_score              INTEGER NOT NULL CHECK (m_score BETWEEN 1 AND 5),
    rfm_cell             TEXT    NOT NULL CHECK (length(rfm_cell) = 3),
    rfm_score            INTEGER NOT NULL CHECK (rfm_score BETWEEN 3 AND 15),
    fm_score             REAL    NOT NULL CHECK (fm_score BETWEEN 1 AND 5),
    rfm_segment          TEXT    NOT NULL REFERENCES rfm_segment_definitions (segment_name),
    first_purchase_date  DATE    NOT NULL,
    last_purchase_date   DATE    NOT NULL,
    acquisition_status   TEXT    NOT NULL CHECK (acquisition_status IN ('Existing before 2023', 'Acquired 2023-2025')),
    CHECK (rfm_score = r_score + f_score + m_score),
    CHECK (first_purchase_date <= last_purchase_date)
);

-- -----------------------------------------------------------------------------
-- 8. ml_clusters — the 4 K-Means clusters of Step 6 (labels attached after profiling)
-- -----------------------------------------------------------------------------
CREATE TABLE ml_clusters (
    cluster_id     INTEGER PRIMARY KEY CHECK (cluster_id >= 0),
    cluster_label  TEXT    NOT NULL UNIQUE,
    model          TEXT    NOT NULL                              -- e.g. KMeans(k=4) on log1p + scaled R, F, M
);

-- -----------------------------------------------------------------------------
-- 9. customer_segments — Step 6 cluster assignment per customer
-- -----------------------------------------------------------------------------
CREATE TABLE customer_segments (
    customer_id  TEXT    PRIMARY KEY REFERENCES customers (customer_id),
    cluster_id   INTEGER NOT NULL REFERENCES ml_clusters (cluster_id),
    silhouette   REAL    CHECK (silhouette BETWEEN -1 AND 1),
    pc1          REAL,
    pc2          REAL
);

-- -----------------------------------------------------------------------------
-- 10. customer_value — Step 7 CLV: observed historical value + ESTIMATED next-12-month profit
-- -----------------------------------------------------------------------------
CREATE TABLE customer_value (
    customer_id                     TEXT    PRIMARY KEY REFERENCES customers (customer_id),
    historical_revenue_clv          REAL    NOT NULL CHECK (historical_revenue_clv > 0),   -- observed 2023-2025
    historical_profit_clv           REAL    NOT NULL,                                      -- observed; may be < 0
    estimated_12m_future_profit     REAL    NOT NULL CHECK (estimated_12m_future_profit >= 0),  -- model estimate
    estimate_method                 TEXT    NOT NULL,
    simplified_12m_estimate         REAL    CHECK (simplified_12m_estimate >= 0),
    illustrative_3y_value           REAL    CHECK (illustrative_3y_value >= 0),                 -- not validated
    high_historical_value           INTEGER NOT NULL CHECK (high_historical_value IN (0, 1)),
    high_estimated_future_value     INTEGER NOT NULL CHECK (high_estimated_future_value IN (0, 1)),
    high_value_high_engagement      INTEGER NOT NULL CHECK (high_value_high_engagement IN (0, 1)),
    potentially_at_risk_high_value  INTEGER NOT NULL CHECK (potentially_at_risk_high_value IN (0, 1)),
    future_value_opportunity        INTEGER NOT NULL CHECK (future_value_opportunity IN (0, 1))
);

-- -----------------------------------------------------------------------------
-- 11. revenue_forecasts — Step 9 monthly actuals and forecasts (selected model)
-- -----------------------------------------------------------------------------
CREATE TABLE revenue_forecasts (
    month             TEXT NOT NULL CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]'),   -- 'YYYY-MM'
    record_type       TEXT NOT NULL
                      CHECK (record_type IN ('Historical actual', 'Validation forecast (fit on train)',
                                             'Test forecast (fit on train + validation)',
                                             'Future forecast (fit on all 36 months)')),
    actual_revenue    REAL,                 -- NULL for future months
    forecast_revenue  REAL,                 -- NULL for historical actual rows
    lower_80          REAL,
    upper_80          REAL,
    lower_95          REAL,
    upper_95          REAL,
    model             TEXT,
    PRIMARY KEY (month, record_type),
    CHECK (lower_95 IS NULL OR (lower_95 <= forecast_revenue AND forecast_revenue <= upper_95))
);

CREATE INDEX idx_rfm_segment      ON customer_rfm      (rfm_segment);
CREATE INDEX idx_segments_cluster ON customer_segments (cluster_id);

-- -----------------------------------------------------------------------------
-- vw_delivered_sales — Delivered lines only (the project-wide revenue rule), with the attributes most analyses need.
-- Revenue = Sales on Delivered lines; Returned / Cancelled lines carry no revenue.
-- -----------------------------------------------------------------------------
CREATE VIEW vw_delivered_sales AS
SELECT
    oi.order_line_id, o.order_id, o.order_date,
    CAST(strftime('%Y', o.order_date) AS INTEGER) AS order_year,
    strftime('%Y-%m', o.order_date)               AS order_month,
    o.customer_id, o.customer_type, o.payment_method,
    l.region, l.state, l.city,
    p.product_id, p.product_name, p.category, p.sub_category,
    oi.quantity, oi.unit_price, oi.discount, oi.sales, oi.cost, oi.profit
FROM order_items oi
JOIN orders    o ON o.order_id    = oi.order_id
JOIN customers c ON c.customer_id = o.customer_id
JOIN locations l ON l.location_id = c.location_id
JOIN products  p ON p.product_id  = oi.product_id
WHERE oi.order_status = 'Delivered';
