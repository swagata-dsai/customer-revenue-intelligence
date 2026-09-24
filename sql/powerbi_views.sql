-- =============================================================================
-- Customer Revenue Intelligence - STEP 11: Power BI star-schema layer
-- SYNTHETIC DATA (generated for an internship project; not real customers)
--
-- These views sit on top of the validated Step 10 database. Power BI imports
-- them as CSV files exported by src/powerbi_prep.py, so the dashboard reads
-- exactly the rows that the SQL validation checked.
--
--   Facts : pbi_fact_sales (order-line grain), pbi_fact_forecast (month grain)
--   Dims  : pbi_dim_date, pbi_dim_customer, pbi_dim_product, pbi_dim_geography,
--           pbi_dim_rfm_segment, pbi_dim_cluster
--
-- Privacy: customer names are NOT exposed; analytical outputs use Customer_ID.
-- Revenue rule (unchanged since Step 3): only Delivered lines count as revenue.
-- The fact keeps every line with an Is_Delivered flag so the return /
-- cancellation analysis stays possible; every revenue measure filters on it.
-- =============================================================================

DROP VIEW IF EXISTS pbi_dim_date;
DROP VIEW IF EXISTS pbi_dim_geography;
DROP VIEW IF EXISTS pbi_dim_product;
DROP VIEW IF EXISTS pbi_dim_rfm_segment;
DROP VIEW IF EXISTS pbi_dim_cluster;
DROP VIEW IF EXISTS pbi_dim_customer;
DROP VIEW IF EXISTS pbi_fact_sales;
DROP VIEW IF EXISTS pbi_fact_forecast;

-- -----------------------------------------------------------------------------
-- DimDate: one row per day, 2023-01-01 .. 2026-06-30
-- (36 historical months + the 6-month Step 9 forecast horizon).
-- Week_Number is the ISO-8601 week, which matches Order_Week in the cleaned
-- data. SQLite 3.45 has no %V, so it is derived from the Thursday of each week.
-- The Financial_* columns follow the Indian April-March financial-year
-- convention as a standard calendar attribute; the dataset does not state a
-- company fiscal year.
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_date AS
WITH RECURSIVE d(dt) AS (
    SELECT date('2023-01-01')
    UNION ALL
    SELECT date(dt, '+1 day') FROM d WHERE dt < date('2026-06-30')
),
x AS (
    SELECT dt,
           CAST(strftime('%Y', dt) AS INTEGER)                              AS yr,
           CAST(strftime('%m', dt) AS INTEGER)                              AS mo,
           CAST(strftime('%d', dt) AS INTEGER)                              AS dy,
           (CAST(strftime('%w', dt) AS INTEGER) + 6) % 7 + 1                AS dow,      -- 1 = Monday
           date(dt, '-' || ((CAST(strftime('%w', dt) AS INTEGER) + 6) % 7) || ' days', '+3 days') AS iso_thu
    FROM d
)
SELECT
    dt                                                                       AS Date,
    yr                                                                       AS Year,
    'Q' || ((mo - 1) / 3 + 1)                                                AS Quarter,
    (mo - 1) / 3 + 1                                                         AS Quarter_Number,
    yr || '-Q' || ((mo - 1) / 3 + 1)                                         AS Year_Quarter,
    yr * 10 + (mo - 1) / 3 + 1                                               AS Year_Quarter_Sort,
    mo                                                                       AS Month_Number,
    CASE mo WHEN 1 THEN 'January' WHEN 2 THEN 'February' WHEN 3 THEN 'March'
            WHEN 4 THEN 'April' WHEN 5 THEN 'May' WHEN 6 THEN 'June'
            WHEN 7 THEN 'July' WHEN 8 THEN 'August' WHEN 9 THEN 'September'
            WHEN 10 THEN 'October' WHEN 11 THEN 'November' ELSE 'December' END AS Month_Name,
    CASE mo WHEN 1 THEN 'Jan' WHEN 2 THEN 'Feb' WHEN 3 THEN 'Mar' WHEN 4 THEN 'Apr'
            WHEN 5 THEN 'May' WHEN 6 THEN 'Jun' WHEN 7 THEN 'Jul' WHEN 8 THEN 'Aug'
            WHEN 9 THEN 'Sep' WHEN 10 THEN 'Oct' WHEN 11 THEN 'Nov' ELSE 'Dec' END AS Month_Short,
    strftime('%Y-%m', dt)                                                    AS Year_Month,
    yr * 100 + mo                                                            AS Year_Month_Sort,
    date(dt, 'start of month')                                               AS Month_Start_Date,
    (CAST(strftime('%j', iso_thu) AS INTEGER) - 1) / 7 + 1                   AS Week_Number,
    CAST(strftime('%Y', iso_thu) AS INTEGER)                                 AS ISO_Week_Year,
    dy                                                                       AS Day,
    dow                                                                      AS Day_Of_Week_Number,
    CASE dow WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday' WHEN 3 THEN 'Wednesday'
             WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday'
             ELSE 'Sunday' END                                               AS Day_Name,
    CASE WHEN dow >= 6 THEN 1 ELSE 0 END                                     AS Is_Weekend,
    CASE WHEN mo >= 4 THEN 'FY' || yr || '-' || substr(yr + 1, 3, 2)
         ELSE 'FY' || (yr - 1) || '-' || substr(yr, 3, 2) END               AS Financial_Year,
    CASE WHEN mo >= 4 THEN yr ELSE yr - 1 END                                AS Financial_Year_Start,
    'FQ' || (((mo + 8) % 12) / 3 + 1)                                        AS Financial_Quarter,
    (mo + 8) % 12 + 1                                                        AS Financial_Month_Number,
    CASE WHEN dt <= date('2025-12-31') THEN 'Historical' ELSE 'Forecast horizon' END AS Period_Type
FROM x;

-- -----------------------------------------------------------------------------
-- DimGeography: customer home location (35 cities). Country added so Power BI
-- geocodes city names unambiguously if a map is used.
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_geography AS
SELECT location_id AS Location_ID,
       city        AS City,
       state       AS State,
       region      AS Region,
       'India'     AS Country
FROM locations;

-- -----------------------------------------------------------------------------
-- DimProduct
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_product AS
SELECT product_id   AS Product_ID,
       product_name AS Product_Name,
       category     AS Category,
       sub_category AS Sub_Category
FROM products;

-- -----------------------------------------------------------------------------
-- DimRFMSegment: the Step 5 rule-based segments plus a member for the 16
-- registered customers who never had a delivered order (so no blank row).
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_rfm_segment AS
SELECT segment_name         AS RFM_Segment,
       priority             AS Segment_Order,
       value_activity_group AS Value_Activity_Group,
       CASE value_activity_group WHEN 'Active high value' THEN 1 WHEN 'Developing' THEN 2
                                 WHEN 'Slipping' THEN 3 WHEN 'Inactive' THEN 4 ELSE 5 END AS Group_Order,
       rule_text            AS Segment_Rule,
       business_meaning     AS Business_Meaning
FROM rfm_segment_definitions
UNION ALL
SELECT 'No delivered order', 12, 'No delivered order', 5,
       'Registered customer with no Delivered order line (not scored by RFM)',
       'Not part of the RFM or K-Means analysis';

-- -----------------------------------------------------------------------------
-- DimCluster: the Step 6 K-Means clusters (+ -1 for customers not clustered).
-- Cluster_Order ranks clusters by revenue per customer (computed, not assumed).
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_cluster AS
WITH rev AS (
    SELECT s.cluster_id, SUM(v.sales) / COUNT(DISTINCT v.customer_id) AS rev_per_customer
    FROM customer_segments s
    JOIN vw_delivered_sales v ON v.customer_id = s.customer_id
    GROUP BY s.cluster_id
)
SELECT m.cluster_id                                                   AS Cluster_ID,
       m.cluster_label                                                AS Cluster_Label,
       ROW_NUMBER() OVER (ORDER BY r.rev_per_customer DESC)           AS Cluster_Order,
       m.model                                                        AS Model
FROM ml_clusters m
JOIN rev r ON r.cluster_id = m.cluster_id
UNION ALL
SELECT -1, 'No delivered order', 99, 'Not clustered';

-- -----------------------------------------------------------------------------
-- DimCustomer: one row per registered customer (2,000). No names.
-- RFM (Step 5), cluster (Step 6) and CLV (Step 7) attributes are snapshots at
-- the reference date 2026-01-01; they are folded in here so every customer
-- attribute sits in one dimension. Activity status uses the Step 7 180-day
-- threshold and is "inactivity", never "churn".
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_dim_customer AS
SELECT c.customer_id                                                            AS Customer_ID,
       c.customer_age                                                           AS Customer_Age,
       CASE WHEN c.customer_age <= 24 THEN '18-24' WHEN c.customer_age <= 34 THEN '25-34'
            WHEN c.customer_age <= 49 THEN '35-49' ELSE '50+' END               AS Age_Band,
       c.gender                                                                 AS Gender,
       l.region                                                                 AS Home_Region,
       CASE WHEN r.customer_id IS NULL THEN 0 ELSE 1 END                        AS Has_Delivered_Order,
       r.reference_date                                                         AS Reference_Date,
       r.first_purchase_date                                                    AS First_Purchase_Date,
       r.last_purchase_date                                                     AS Last_Purchase_Date,
       COALESCE(r.acquisition_status, 'No delivered order')                     AS Acquisition_Status,
       r.recency_days                                                           AS Recency_Days,
       r.frequency_orders                                                       AS Frequency_Orders,
       r.monetary_revenue                                                       AS Monetary_Revenue,
       r.r_score                                                                AS R_Score,
       r.f_score                                                                AS F_Score,
       r.m_score                                                                AS M_Score,
       r.rfm_cell                                                               AS RFM_Cell,
       r.rfm_score                                                              AS RFM_Score,
       COALESCE(r.rfm_segment, 'No delivered order')                            AS RFM_Segment,
       COALESCE(s.cluster_id, -1)                                               AS Cluster_ID,
       CASE WHEN r.customer_id IS NULL THEN 'No delivered order'
            WHEN r.recency_days < 180 THEN 'Active (< 180 days)'
            WHEN r.recency_days < 365 THEN 'Inactive 180-364 days'
            ELSE 'Inactive 365+ days' END                                       AS Activity_Status,
       CASE WHEN r.customer_id IS NULL THEN 9
            WHEN r.recency_days < 180 THEN 1
            WHEN r.recency_days < 365 THEN 2 ELSE 3 END                         AS Activity_Status_Order,
       CASE WHEN r.customer_id IS NULL THEN 'No delivered order'
            WHEN r.recency_days < 30 THEN '0-29 days'
            WHEN r.recency_days < 90 THEN '30-89 days'
            WHEN r.recency_days < 180 THEN '90-179 days'
            WHEN r.recency_days < 365 THEN '180-364 days'
            ELSE '365+ days' END                                                AS Recency_Band,
       CASE WHEN r.customer_id IS NULL THEN 9
            WHEN r.recency_days < 30 THEN 1 WHEN r.recency_days < 90 THEN 2
            WHEN r.recency_days < 180 THEN 3 WHEN r.recency_days < 365 THEN 4
            ELSE 5 END                                                          AS Recency_Band_Order,
       CASE WHEN r.customer_id IS NULL THEN 'No delivered order'
            WHEN r.frequency_orders = 1 THEN '1 order'
            WHEN r.frequency_orders <= 3 THEN '2-3 orders'
            WHEN r.frequency_orders <= 6 THEN '4-6 orders'
            WHEN r.frequency_orders <= 10 THEN '7-10 orders'
            ELSE '11+ orders' END                                               AS Frequency_Band,
       CASE WHEN r.customer_id IS NULL THEN 9
            WHEN r.frequency_orders = 1 THEN 1 WHEN r.frequency_orders <= 3 THEN 2
            WHEN r.frequency_orders <= 6 THEN 3 WHEN r.frequency_orders <= 10 THEN 4
            ELSE 5 END                                                          AS Frequency_Band_Order,
       v.historical_revenue_clv                                                 AS Historical_Revenue_CLV,
       v.historical_profit_clv                                                  AS Historical_Profit_CLV,
       v.estimated_12m_future_profit                                            AS Estimated_12M_Future_Profit,
       v.estimate_method                                                        AS Estimate_Method,
       v.illustrative_3y_value                                                  AS Illustrative_3Y_Value,
       v.high_historical_value                                                  AS High_Historical_Value,
       v.high_estimated_future_value                                            AS High_Estimated_Future_Value,
       v.high_value_high_engagement                                             AS High_Value_High_Engagement,
       v.potentially_at_risk_high_value                                         AS Potentially_At_Risk_High_Value,
       v.future_value_opportunity                                               AS Future_Value_Opportunity
FROM customers c
JOIN locations l            ON l.location_id = c.location_id
LEFT JOIN customer_rfm r    ON r.customer_id = c.customer_id
LEFT JOIN customer_segments s ON s.customer_id = c.customer_id
LEFT JOIN customer_value v  ON v.customer_id = c.customer_id;

-- -----------------------------------------------------------------------------
-- FactSales: order-line grain, ALL statuses (18,670 lines) with Is_Delivered.
-- Location_ID is the customer's home location at order time (one location per
-- customer in this dataset), giving FactSales a direct key to DimGeography.
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_fact_sales AS
SELECT i.order_line_id                                                 AS Order_Line_ID,
       i.order_id                                                      AS Order_ID,
       o.order_date                                                    AS Order_Date,
       o.customer_id                                                   AS Customer_ID,
       i.product_id                                                    AS Product_ID,
       c.location_id                                                   AS Location_ID,
       o.payment_method                                                AS Payment_Method,
       o.customer_type                                                 AS Customer_Type,
       i.order_status                                                  AS Order_Status,
       CASE WHEN i.order_status = 'Delivered' THEN 1 ELSE 0 END        AS Is_Delivered,
       i.quantity                                                      AS Quantity,
       i.unit_price                                                    AS Unit_Price,
       i.discount                                                      AS Discount,
       CASE WHEN i.discount = 0 THEN '0%'
            WHEN i.discount <= 0.10 THEN '1-10%'
            WHEN i.discount <= 0.20 THEN '11-20%'
            WHEN i.discount <= 0.30 THEN '21-30%'
            ELSE '31-40%' END                                          AS Discount_Band,
       CASE WHEN i.discount = 0 THEN 1
            WHEN i.discount <= 0.10 THEN 2
            WHEN i.discount <= 0.20 THEN 3
            WHEN i.discount <= 0.30 THEN 4
            ELSE 5 END                                                 AS Discount_Band_Order,
       ROUND(i.quantity * i.unit_price * (1 - i.discount), 2)          AS Booked_Value,
       i.sales                                                         AS Sales,
       i.cost                                                          AS Cost,
       i.profit                                                        AS Profit
FROM order_items i
JOIN orders o    ON o.order_id = i.order_id
JOIN customers c ON c.customer_id = o.customer_id;

-- -----------------------------------------------------------------------------
-- FactForecast: Step 9 monthly revenue - historical actuals, validation and
-- test back-forecasts, and the 6-month future forecast with 80% / 95%
-- prediction intervals. Company level only (not by region or category).
-- -----------------------------------------------------------------------------
CREATE VIEW pbi_fact_forecast AS
SELECT month || '-01'                                                  AS Month_Date,
       month                                                           AS Year_Month,
       record_type                                                     AS Record_Type,
       CASE record_type
            WHEN 'Historical actual' THEN 'Historical'
            WHEN 'Future forecast (fit on all 36 months)' THEN 'Forecast'
            ELSE 'Forecast (backtest)' END                             AS Series_Label,
       CASE record_type
            WHEN 'Historical actual' THEN 1
            WHEN 'Validation forecast (fit on train)' THEN 2
            WHEN 'Test forecast (fit on train + validation)' THEN 3
            ELSE 4 END                                                 AS Record_Type_Order,
       actual_revenue                                                  AS Actual_Revenue,
       forecast_revenue                                                AS Forecast_Revenue,
       lower_80                                                        AS Lower_80,
       upper_80                                                        AS Upper_80,
       lower_95                                                        AS Lower_95,
       upper_95                                                        AS Upper_95,
       CASE WHEN actual_revenue IS NOT NULL AND forecast_revenue IS NOT NULL
            THEN forecast_revenue - actual_revenue END                 AS Forecast_Error,
       model                                                           AS Model
FROM revenue_forecasts;
