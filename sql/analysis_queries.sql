-- =============================================================================
-- analysis_queries.sql — Customer Revenue Intelligence (SYNTHETIC DATA)
-- =============================================================================
-- Dialect: SQLite 3.25+ (window functions). Database: data/customer_revenue_intelligence.db
-- Revenue rule (whole project): revenue, cost and profit count only Delivered order lines
--   -> every revenue query reads the view vw_delivered_sales.
-- The reference date is never typed in: it is computed as (last order date + 1 day).
-- Each query starts with a header parsed by src/sql_analytics.py:
--   -- name: <id>   -- section: <section>   -- title: <what it answers>
-- Results are saved to outputs/tables/sql/<id>.csv. Customer outputs use customer_id only (no names).
-- =============================================================================


-- =============================================================================
-- 1. REVENUE ANALYSIS
-- =============================================================================

-- name: rev_kpi_summary
-- section: Revenue
-- title: Headline KPIs - total revenue, profit, margin, orders, customers, AOV
SELECT
    ROUND(SUM(sales), 2)                                   AS total_revenue,
    ROUND(SUM(cost), 2)                                    AS total_cost,
    ROUND(SUM(profit), 2)                                  AS total_profit,
    ROUND(100.0 * SUM(profit) / SUM(sales), 2)             AS profit_margin_pct,
    COUNT(DISTINCT order_id)                               AS total_orders,
    COUNT(DISTINCT customer_id)                            AS total_customers,
    ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)        AS average_order_value,
    COUNT(*)                                               AS order_lines,
    SUM(quantity)                                          AS units_sold,
    MIN(order_date)                                        AS first_order_date,
    MAX(order_date)                                        AS last_order_date
FROM vw_delivered_sales;

-- name: rev_order_status
-- section: Revenue
-- title: Order lines and booked value by status (why only Delivered lines count as revenue)
SELECT
    order_status,
    COUNT(*)                                               AS order_lines,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)     AS pct_of_lines,
    ROUND(SUM(quantity * unit_price * (1 - discount)), 2)  AS booked_value
FROM order_items
GROUP BY order_status
ORDER BY order_lines DESC;

-- name: rev_by_year
-- section: Revenue
-- title: Revenue, profit and margin by year with year-over-year growth
WITH yearly AS (
    SELECT order_year,
           SUM(sales)               AS revenue,
           SUM(profit)              AS profit,
           COUNT(DISTINCT order_id) AS orders,
           COUNT(DISTINCT customer_id) AS customers
    FROM vw_delivered_sales
    GROUP BY order_year
)
SELECT order_year,
       ROUND(revenue, 2)                                              AS revenue,
       ROUND(profit, 2)                                               AS profit,
       ROUND(100.0 * profit / revenue, 2)                             AS profit_margin_pct,
       orders, customers,
       ROUND(revenue / orders, 2)                                     AS average_order_value,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_year))
             / LAG(revenue) OVER (ORDER BY order_year), 2)            AS revenue_yoy_growth_pct,
       ROUND(100.0 * (profit - LAG(profit) OVER (ORDER BY order_year))
             / LAG(profit) OVER (ORDER BY order_year), 2)             AS profit_yoy_growth_pct
FROM yearly
ORDER BY order_year;

-- name: rev_by_quarter
-- section: Revenue
-- title: Quarterly revenue with quarter-on-quarter and same-quarter-last-year growth
WITH q AS (
    SELECT order_year,
           (CAST(strftime('%m', order_date) AS INTEGER) + 2) / 3 AS quarter,
           SUM(sales) AS revenue, SUM(profit) AS profit
    FROM vw_delivered_sales
    GROUP BY order_year, quarter
)
SELECT order_year || '-Q' || quarter                                       AS year_quarter,
       ROUND(revenue, 2)                                                   AS revenue,
       ROUND(profit, 2)                                                    AS profit,
       ROUND(100.0 * (revenue / LAG(revenue, 1) OVER w - 1), 2)            AS qoq_growth_pct,
       ROUND(100.0 * (revenue / LAG(revenue, 4) OVER w - 1), 2)            AS yoy_growth_pct
FROM q
WINDOW w AS (ORDER BY order_year, quarter)
ORDER BY order_year, quarter;

-- name: rev_margin_by_year_category
-- section: Revenue
-- title: Profit margin by year and category (is margin stable over time?)
SELECT order_year, category,
       ROUND(SUM(sales), 2)                            AS revenue,
       ROUND(SUM(profit), 2)                           AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)      AS profit_margin_pct
FROM vw_delivered_sales
GROUP BY order_year, category
ORDER BY category, order_year;


-- =============================================================================
-- 2. CUSTOMER ANALYTICS
-- =============================================================================

-- name: cust_top_revenue
-- section: Customer
-- title: Top 20 customers by revenue (with rank and share of total)
WITH c AS (
    SELECT customer_id, SUM(sales) AS revenue, SUM(profit) AS profit, COUNT(DISTINCT order_id) AS orders
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT RANK() OVER (ORDER BY revenue DESC)                      AS revenue_rank,
       customer_id,
       ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit, orders,
       ROUND(revenue / orders, 2)                                AS average_order_value,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 3)          AS pct_of_total_revenue
FROM c
ORDER BY revenue DESC
LIMIT 20;

-- name: cust_top_profit
-- section: Customer
-- title: Top 20 customers by profit (with margin)
SELECT customer_id,
       ROUND(SUM(profit), 2)                           AS profit,
       ROUND(SUM(sales), 2)                            AS revenue,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)      AS profit_margin_pct,
       COUNT(DISTINCT order_id)                        AS orders
FROM vw_delivered_sales
GROUP BY customer_id
ORDER BY profit DESC
LIMIT 20;

-- name: cust_most_frequent
-- section: Customer
-- title: Most frequent customers (10+ delivered orders)
SELECT customer_id,
       COUNT(DISTINCT order_id)                                        AS orders,
       ROUND(SUM(sales), 2)                                            AS revenue,
       MIN(order_date)                                                 AS first_order,
       MAX(order_date)                                                 AS last_order,
       ROUND((julianday(MAX(order_date)) - julianday(MIN(order_date)))
             / NULLIF(COUNT(DISTINCT order_id) - 1, 0), 1)             AS avg_days_between_orders
FROM vw_delivered_sales
GROUP BY customer_id
HAVING COUNT(DISTINCT order_id) >= 10
ORDER BY orders DESC, revenue DESC
LIMIT 25;

-- name: cust_highest_aov
-- section: Customer
-- title: Highest average order value (customers with >= 3 orders, to avoid one-off noise)
SELECT customer_id,
       COUNT(DISTINCT order_id)                           AS orders,
       ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)    AS average_order_value,
       ROUND(SUM(sales), 2)                               AS revenue
FROM vw_delivered_sales
GROUP BY customer_id
HAVING COUNT(DISTINCT order_id) >= 3
ORDER BY average_order_value DESC
LIMIT 20;

-- name: cust_new_vs_existing
-- section: Customer
-- title: New vs existing customers (customer type on each customer's first order)
WITH first_order AS (
    SELECT customer_id, customer_type,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS rn
    FROM orders
),
cust AS (
    SELECT f.customer_id,
           CASE f.customer_type WHEN 'New' THEN 'Acquired 2023-2025' ELSE 'Existing before 2023' END AS acquisition_status
    FROM first_order f
    WHERE f.rn = 1
)
SELECT c.acquisition_status,
       COUNT(DISTINCT c.customer_id)                                   AS customers,
       COUNT(DISTINCT d.customer_id)                                   AS customers_with_delivered_order,
       ROUND(SUM(d.sales), 2)                                          AS revenue,
       ROUND(100.0 * SUM(d.sales) / (SELECT SUM(sales) FROM vw_delivered_sales), 2) AS pct_of_revenue,
       ROUND(SUM(d.sales) / COUNT(DISTINCT d.customer_id), 2)          AS revenue_per_customer,
       ROUND(1.0 * COUNT(DISTINCT d.order_id) / COUNT(DISTINCT d.customer_id), 2) AS orders_per_customer
FROM cust c
LEFT JOIN vw_delivered_sales d ON d.customer_id = c.customer_id
GROUP BY c.acquisition_status;

-- name: cust_acquired_by_year
-- section: Customer
-- title: Customers by year of first delivered purchase (cohorts) and their revenue to date
WITH first_buy AS (
    SELECT customer_id, MIN(order_year) AS cohort_year
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT f.cohort_year,
       COUNT(DISTINCT f.customer_id)                                   AS customers,
       ROUND(SUM(d.sales), 2)                                          AS revenue_to_date,
       ROUND(SUM(d.sales) / COUNT(DISTINCT f.customer_id), 2)          AS revenue_per_customer
FROM first_buy f
JOIN vw_delivered_sales d ON d.customer_id = f.customer_id
GROUP BY f.cohort_year
ORDER BY f.cohort_year;

-- name: cust_frequency_distribution
-- section: Customer
-- title: Customer purchase frequency distribution (delivered orders per customer)
WITH c AS (
    SELECT customer_id, COUNT(DISTINCT order_id) AS orders, SUM(sales) AS revenue
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT CASE WHEN orders = 1 THEN '1 order'
            WHEN orders BETWEEN 2 AND 3 THEN '2-3 orders'
            WHEN orders BETWEEN 4 AND 6 THEN '4-6 orders'
            WHEN orders BETWEEN 7 AND 10 THEN '7-10 orders'
            ELSE '11+ orders' END                                      AS frequency_band,
       MIN(orders)                                                     AS band_min,
       COUNT(*)                                                        AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)              AS pct_of_customers,
       ROUND(SUM(revenue), 2)                                          AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2)      AS pct_of_revenue
FROM c
GROUP BY frequency_band
ORDER BY band_min;

-- name: cust_revenue_concentration
-- section: Customer
-- title: Customer revenue concentration - rank, cumulative revenue and cumulative % (Pareto)
WITH c AS (
    SELECT customer_id, SUM(sales) AS revenue
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT ROW_NUMBER() OVER (ORDER BY revenue DESC, customer_id)                            AS customer_rank,
       customer_id,
       ROUND(revenue, 2)                                                                  AS customer_revenue,
       ROUND(SUM(revenue) OVER (ORDER BY revenue DESC, customer_id ROWS UNBOUNDED PRECEDING), 2) AS cumulative_revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 4)                                   AS pct_of_total_revenue,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC, customer_id ROWS UNBOUNDED PRECEDING)
             / SUM(revenue) OVER (), 3)                                                   AS cumulative_pct_of_revenue,
       ROUND(100.0 * ROW_NUMBER() OVER (ORDER BY revenue DESC, customer_id) / COUNT(*) OVER (), 3) AS cumulative_pct_of_customers
FROM c
ORDER BY customer_rank;

-- name: cust_concentration_summary
-- section: Customer
-- title: Share of revenue held by the top 1% / 5% / 10% / 20% / 50% of customers
WITH c AS (
    SELECT customer_id, SUM(sales) AS revenue FROM vw_delivered_sales GROUP BY customer_id
),
r AS (
    SELECT revenue, ROW_NUMBER() OVER (ORDER BY revenue DESC, customer_id) AS rk, COUNT(*) OVER () AS n
    FROM c
),
t(top_pct) AS (VALUES (1), (5), (10), (20), (50))
SELECT t.top_pct,
       CAST(ROUND(MAX(r.n) * t.top_pct / 100.0) AS INTEGER)                              AS customers,
       ROUND(100.0 * SUM(CASE WHEN r.rk <= ROUND(r.n * t.top_pct / 100.0) THEN r.revenue END)
             / SUM(r.revenue), 2)                                                        AS pct_of_revenue
FROM t CROSS JOIN r
GROUP BY t.top_pct
ORDER BY t.top_pct;

-- name: cust_inactive
-- section: Customer
-- title: Customers with no purchase for >= 90 / 180 / 365 days (inactivity, NOT churn - see Step 7)
WITH ref AS (SELECT date(MAX(order_date), '+1 day') AS ref_date FROM orders),
last_buy AS (
    SELECT customer_id, MAX(order_date) AS last_order, SUM(sales) AS revenue
    FROM vw_delivered_sales
    GROUP BY customer_id
),
t(days) AS (VALUES (90), (180), (365))
SELECT t.days                                                                     AS inactive_for_at_least_days,
       (SELECT ref_date FROM ref)                                                 AS reference_date,
       SUM(CASE WHEN julianday((SELECT ref_date FROM ref)) - julianday(l.last_order) >= t.days THEN 1 ELSE 0 END) AS customers,
       ROUND(100.0 * SUM(CASE WHEN julianday((SELECT ref_date FROM ref)) - julianday(l.last_order) >= t.days THEN 1 ELSE 0 END)
             / COUNT(*), 2)                                                       AS pct_of_customers,
       ROUND(SUM(CASE WHEN julianday((SELECT ref_date FROM ref)) - julianday(l.last_order) >= t.days
                      THEN l.revenue ELSE 0 END), 2)                               AS their_lifetime_revenue
FROM t CROSS JOIN last_buy l
GROUP BY t.days
ORDER BY t.days;


-- =============================================================================
-- 3. RFM & ML SEGMENTATION (analysing the Python outputs; nothing is re-segmented in SQL)
-- =============================================================================

-- name: seg_rfm_summary
-- section: Segmentation
-- title: RFM segment summary - customers, revenue, profit, average revenue / frequency / recency, contribution %
WITH cust AS (                                   -- revenue and profit recomputed from the transactions
    SELECT customer_id, SUM(sales) AS revenue, SUM(profit) AS profit
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT r.rfm_segment                                                        AS segment,
       d.value_activity_group,
       COUNT(*)                                                             AS customer_count,
       ROUND(SUM(c.revenue), 2)                                             AS revenue,
       ROUND(SUM(c.profit), 2)                                              AS profit,
       ROUND(AVG(c.revenue), 2)                                             AS avg_revenue_per_customer,
       ROUND(AVG(r.frequency_orders), 2)                                    AS avg_frequency,
       ROUND(AVG(r.recency_days), 1)                                        AS avg_recency_days,
       ROUND(100.0 * SUM(c.revenue) / SUM(SUM(c.revenue)) OVER (), 2)       AS revenue_contribution_pct,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                   AS customer_pct
FROM customer_rfm r
JOIN rfm_segment_definitions d ON d.segment_name = r.rfm_segment
JOIN cust c                    ON c.customer_id  = r.customer_id
GROUP BY r.rfm_segment, d.value_activity_group, d.priority
ORDER BY d.priority;

-- name: seg_value_activity_groups
-- section: Segmentation
-- title: Revenue and customers by value-activity group (rolled up from the RFM segment definitions)
SELECT d.value_activity_group,
       COUNT(*)                                                             AS customers,
       ROUND(SUM(r.monetary_revenue), 2)                                    AS revenue,
       ROUND(100.0 * SUM(r.monetary_revenue) / SUM(SUM(r.monetary_revenue)) OVER (), 2) AS revenue_contribution_pct
FROM customer_rfm r
JOIN rfm_segment_definitions d ON d.segment_name = r.rfm_segment
GROUP BY d.value_activity_group
ORDER BY revenue DESC;

-- name: seg_ml_cluster_summary
-- section: Segmentation
-- title: ML cluster size, revenue, profit and contribution (Step 6 K-Means)
SELECT m.cluster_id, m.cluster_label,
       COUNT(DISTINCT s.customer_id)                                        AS customer_count,
       ROUND(100.0 * COUNT(DISTINCT s.customer_id)
             / (SELECT COUNT(*) FROM customer_segments), 2)                  AS customer_pct,
       ROUND(SUM(d.sales), 2)                                               AS revenue,
       ROUND(SUM(d.profit), 2)                                              AS profit,
       ROUND(100.0 * SUM(d.profit) / SUM(d.sales), 2)                       AS profit_margin_pct,
       ROUND(100.0 * SUM(d.sales) / (SELECT SUM(sales) FROM vw_delivered_sales), 2) AS revenue_contribution_pct,
       ROUND(SUM(d.sales) / COUNT(DISTINCT s.customer_id), 2)               AS revenue_per_customer
FROM ml_clusters m
JOIN customer_segments s  ON s.cluster_id  = m.cluster_id
JOIN vw_delivered_sales d ON d.customer_id = s.customer_id
GROUP BY m.cluster_id, m.cluster_label
ORDER BY m.cluster_id;

-- name: seg_rfm_vs_cluster
-- section: Segmentation
-- title: RFM segment x ML cluster - customer counts (how the two segmentations overlap)
SELECT r.rfm_segment,
       SUM(CASE WHEN s.cluster_id = 0 THEN 1 ELSE 0 END) AS cluster_0,
       SUM(CASE WHEN s.cluster_id = 1 THEN 1 ELSE 0 END) AS cluster_1,
       SUM(CASE WHEN s.cluster_id = 2 THEN 1 ELSE 0 END) AS cluster_2,
       SUM(CASE WHEN s.cluster_id = 3 THEN 1 ELSE 0 END) AS cluster_3,
       COUNT(*)                                          AS total
FROM customer_rfm r
JOIN customer_segments s       ON s.customer_id = r.customer_id
JOIN rfm_segment_definitions d ON d.segment_name = r.rfm_segment
GROUP BY r.rfm_segment, d.priority
ORDER BY d.priority;

-- name: seg_value_by_cluster
-- section: Segmentation
-- title: Observed vs estimated customer value by ML cluster (Step 7 CLV)
SELECT m.cluster_label,
       COUNT(*)                                              AS customers,
       ROUND(AVG(v.historical_profit_clv), 2)                AS avg_historical_profit,
       ROUND(AVG(v.estimated_12m_future_profit), 2)          AS avg_estimated_12m_profit,
       ROUND(SUM(v.estimated_12m_future_profit), 2)          AS total_estimated_12m_profit,
       SUM(v.potentially_at_risk_high_value)                 AS potentially_at_risk_high_value
FROM customer_segments s
JOIN ml_clusters m    ON m.cluster_id  = s.cluster_id
JOIN customer_value v ON v.customer_id = s.customer_id
GROUP BY m.cluster_id, m.cluster_label
ORDER BY m.cluster_id;


-- =============================================================================
-- 4. PRODUCT ANALYTICS
-- =============================================================================

-- name: prod_top_revenue
-- section: Product
-- title: Top 15 products by revenue
SELECT product_id, product_name, category,
       ROUND(SUM(sales), 2)                                 AS revenue,
       SUM(quantity)                                        AS units,
       ROUND(100.0 * SUM(sales) / (SELECT SUM(sales) FROM vw_delivered_sales), 2) AS pct_of_revenue
FROM vw_delivered_sales
GROUP BY product_id, product_name, category
ORDER BY revenue DESC
LIMIT 15;

-- name: prod_top_profit
-- section: Product
-- title: Top 15 products by profit
SELECT product_id, product_name, category,
       ROUND(SUM(profit), 2)                                AS profit,
       ROUND(SUM(sales), 2)                                 AS revenue,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)           AS profit_margin_pct
FROM vw_delivered_sales
GROUP BY product_id, product_name, category
ORDER BY profit DESC
LIMIT 15;

-- name: prod_top_quantity
-- section: Product
-- title: Best-selling products by units sold
SELECT product_id, product_name, category,
       SUM(quantity)                                        AS units,
       COUNT(DISTINCT order_id)                             AS orders,
       ROUND(SUM(sales), 2)                                 AS revenue
FROM vw_delivered_sales
GROUP BY product_id, product_name, category
ORDER BY units DESC
LIMIT 15;

-- name: prod_category_performance
-- section: Product
-- title: Category revenue, profit, margin and share
SELECT category,
       COUNT(DISTINCT product_id)                                      AS products,
       SUM(quantity)                                                   AS units,
       ROUND(SUM(sales), 2)                                            AS revenue,
       ROUND(SUM(profit), 2)                                           AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                      AS profit_margin_pct,
       ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 2)          AS revenue_share_pct,
       ROUND(100.0 * SUM(profit) / SUM(SUM(profit)) OVER (), 2)        AS profit_share_pct,
       RANK() OVER (ORDER BY SUM(profit) / SUM(sales) DESC)            AS margin_rank
FROM vw_delivered_sales
GROUP BY category
ORDER BY revenue DESC;

-- name: prod_subcategory_performance
-- section: Product
-- title: Sub-category revenue, profit and margin (ranked within category)
SELECT category, sub_category,
       ROUND(SUM(sales), 2)                                            AS revenue,
       ROUND(SUM(profit), 2)                                           AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                      AS profit_margin_pct,
       RANK() OVER (PARTITION BY category ORDER BY SUM(sales) DESC)    AS revenue_rank_in_category
FROM vw_delivered_sales
GROUP BY category, sub_category
ORDER BY category, revenue_rank_in_category;

-- name: prod_profitability
-- section: Product
-- title: Product profitability - quantity, revenue, cost, profit, margin, average discount, average price
WITH all_lines AS (
    SELECT product_id,
           COUNT(*)                                                   AS all_lines,
           SUM(CASE WHEN order_status <> 'Delivered' THEN 1 ELSE 0 END) AS returned_or_cancelled_lines
    FROM order_items
    GROUP BY product_id
)
SELECT d.product_id, d.product_name, d.category, d.sub_category,
       SUM(d.quantity)                                                 AS quantity,
       ROUND(SUM(d.sales), 2)                                          AS revenue,
       ROUND(SUM(d.cost), 2)                                           AS cost,
       ROUND(SUM(d.profit), 2)                                         AS profit,
       ROUND(100.0 * SUM(d.profit) / SUM(d.sales), 2)                  AS profit_margin_pct,
       ROUND(100.0 * AVG(d.discount), 2)                               AS avg_discount_pct,
       ROUND(SUM(d.sales) / SUM(d.quantity), 2)                        AS avg_selling_price,
       ROUND(AVG(d.unit_price), 2)                                     AS avg_list_price,
       ROUND(100.0 * a.returned_or_cancelled_lines / a.all_lines, 2)   AS return_cancel_rate_pct,
       RANK() OVER (ORDER BY SUM(d.profit) DESC)                       AS profit_rank
FROM vw_delivered_sales d
LEFT JOIN all_lines a ON a.product_id = d.product_id
GROUP BY d.product_id, d.product_name, d.category, d.sub_category
ORDER BY profit DESC;

-- name: prod_avg_selling_price
-- section: Product
-- title: Average selling price, list price and discount by category
SELECT category,
       ROUND(SUM(sales) / SUM(quantity), 2)            AS avg_selling_price_per_unit,
       ROUND(AVG(unit_price), 2)                       AS avg_list_price,
       ROUND(100.0 * AVG(discount), 2)                 AS avg_discount_pct,
       ROUND(1.0 * SUM(quantity) / COUNT(*), 2)        AS avg_units_per_line
FROM vw_delivered_sales
GROUP BY category
ORDER BY avg_selling_price_per_unit DESC;

-- name: prod_discount_bands
-- section: Product
-- title: Discount level vs revenue, profit and margin
SELECT CASE WHEN discount = 0 THEN '0%'
            WHEN discount <= 0.10 THEN '1-10%'
            WHEN discount <= 0.20 THEN '11-20%'
            WHEN discount <= 0.30 THEN '21-30%'
            ELSE '31-40%' END                                          AS discount_band,
       MIN(discount)                                                   AS band_min,
       COUNT(*)                                                        AS order_lines,
       ROUND(SUM(sales), 2)                                            AS revenue,
       ROUND(SUM(profit), 2)                                           AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                      AS profit_margin_pct,
       ROUND(AVG(sales), 2)                                            AS avg_revenue_per_line,
       ROUND(100.0 * SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS loss_making_lines_pct
FROM vw_delivered_sales
GROUP BY discount_band
ORDER BY band_min;

-- name: prod_investigate
-- section: Product
-- title: Products that may need investigation (margin far below their category, or high return/cancel rate)
WITH p AS (
    SELECT d.product_id, d.product_name, d.category,
           SUM(d.sales) AS revenue, SUM(d.profit) AS profit
    FROM vw_delivered_sales d
    GROUP BY d.product_id, d.product_name, d.category
),
cat AS (
    SELECT category, SUM(profit) / SUM(sales) AS cat_margin FROM vw_delivered_sales GROUP BY category
),
rr AS (
    SELECT product_id, 1.0 * SUM(CASE WHEN order_status <> 'Delivered' THEN 1 ELSE 0 END) / COUNT(*) AS rc_rate
    FROM order_items GROUP BY product_id
),
overall AS (SELECT 1.0 * SUM(CASE WHEN order_status <> 'Delivered' THEN 1 ELSE 0 END) / COUNT(*) AS rc FROM order_items)
SELECT p.product_id, p.product_name, p.category,
       ROUND(p.revenue, 2)                                  AS revenue,
       ROUND(100.0 * p.profit / p.revenue, 2)               AS profit_margin_pct,
       ROUND(100.0 * c.cat_margin, 2)                       AS category_margin_pct,
       ROUND(100.0 * rr.rc_rate, 2)                         AS return_cancel_rate_pct,
       ROUND(100.0 * (SELECT rc FROM overall), 2)           AS overall_return_cancel_rate_pct,
       CASE WHEN p.profit / p.revenue < 0.5 * c.cat_margin AND rr.rc_rate > 1.5 * (SELECT rc FROM overall)
                THEN 'low margin AND high return/cancel rate'
            WHEN p.profit / p.revenue < 0.5 * c.cat_margin THEN 'margin < half of category margin'
            ELSE 'return/cancel rate > 1.5x overall' END   AS reason
FROM p
JOIN cat c ON c.category  = p.category
JOIN rr    ON rr.product_id = p.product_id
WHERE p.profit / p.revenue < 0.5 * c.cat_margin
   OR rr.rc_rate > 1.5 * (SELECT rc FROM overall)
ORDER BY p.revenue DESC;


-- =============================================================================
-- 5. REGIONAL ANALYTICS
-- =============================================================================

-- name: reg_performance
-- section: Regional
-- title: Revenue, profit, orders, customers and AOV by region
SELECT region,
       ROUND(SUM(sales), 2)                                            AS revenue,
       ROUND(SUM(profit), 2)                                           AS profit,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                      AS profit_margin_pct,
       COUNT(DISTINCT order_id)                                        AS orders,
       COUNT(DISTINCT customer_id)                                     AS customers,
       ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)                 AS average_order_value,
       ROUND(SUM(sales) / COUNT(DISTINCT customer_id), 2)              AS revenue_per_customer,
       ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 2)          AS revenue_share_pct
FROM vw_delivered_sales
GROUP BY region
ORDER BY revenue DESC;

-- name: reg_category_matrix
-- section: Regional
-- title: Category performance by region (revenue, margin, share of the region's revenue)
SELECT region, category,
       ROUND(SUM(sales), 2)                                                        AS revenue,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                                  AS profit_margin_pct,
       ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (PARTITION BY region), 2)   AS pct_of_region_revenue,
       RANK() OVER (PARTITION BY region ORDER BY SUM(sales) DESC)                  AS rank_in_region
FROM vw_delivered_sales
GROUP BY region, category
ORDER BY region, rank_in_region;

-- name: reg_top_states
-- section: Regional
-- title: Top 3 states by revenue within each region
WITH s AS (
    SELECT region, state, SUM(sales) AS revenue, COUNT(DISTINCT customer_id) AS customers,
           RANK() OVER (PARTITION BY region ORDER BY SUM(sales) DESC) AS rk
    FROM vw_delivered_sales
    GROUP BY region, state
)
SELECT region, state, rk AS rank_in_region, ROUND(revenue, 2) AS revenue, customers
FROM s
WHERE rk <= 3
ORDER BY region, rk;

-- name: reg_customers_without_orders
-- section: Regional
-- title: Registered customers by region and how many have a Delivered order (LEFT JOIN)
SELECT l.region,
       COUNT(DISTINCT c.customer_id)                                         AS registered_customers,
       COUNT(DISTINCT d.customer_id)                                         AS customers_with_delivered_order,
       COUNT(DISTINCT c.customer_id) - COUNT(DISTINCT d.customer_id)         AS customers_without_delivered_order
FROM customers c
JOIN locations l               ON l.location_id = c.location_id
LEFT JOIN vw_delivered_sales d ON d.customer_id = c.customer_id
GROUP BY l.region
ORDER BY registered_customers DESC;


-- =============================================================================
-- 6. TIME-BASED ANALYSIS
-- =============================================================================

-- name: time_monthly
-- section: Time
-- title: Monthly revenue, profit, orders and customers with month-over-month and year-over-year growth
WITH m AS (
    SELECT order_month,
           SUM(sales) AS revenue, SUM(profit) AS profit,
           COUNT(DISTINCT order_id) AS orders, COUNT(DISTINCT customer_id) AS customers
    FROM vw_delivered_sales
    GROUP BY order_month
)
SELECT order_month,
       ROUND(revenue, 2)                                                   AS revenue,
       ROUND(profit, 2)                                                    AS profit,
       orders, customers,
       ROUND(revenue / orders, 2)                                          AS average_order_value,
       ROUND(100.0 * (revenue / LAG(revenue, 1)  OVER w - 1), 2)           AS mom_growth_pct,
       ROUND(100.0 * (revenue / LAG(revenue, 12) OVER w - 1), 2)           AS yoy_growth_pct,
       ROUND(AVG(revenue) OVER (ORDER BY order_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3m_avg_revenue
FROM m
WINDOW w AS (ORDER BY order_month)
ORDER BY order_month;

-- name: time_best_worst_months
-- section: Time
-- title: Highest- and lowest-revenue months
WITH m AS (
    SELECT order_month, SUM(sales) AS revenue FROM vw_delivered_sales GROUP BY order_month
),
r AS (
    SELECT order_month, revenue,
           RANK() OVER (ORDER BY revenue DESC) AS rank_high,
           RANK() OVER (ORDER BY revenue ASC)  AS rank_low
    FROM m
)
SELECT CASE WHEN rank_high <= 3 THEN 'Top ' || rank_high ELSE 'Bottom ' || rank_low END AS position,
       order_month, ROUND(revenue, 2) AS revenue
FROM r
WHERE rank_high <= 3 OR rank_low <= 3
ORDER BY revenue DESC;

-- name: time_ytd_running_total
-- section: Time
-- title: Year-to-date running revenue by month (running total that restarts each year)
SELECT order_year, order_month,
       ROUND(SUM(sales), 2)                                                             AS revenue,
       ROUND(SUM(SUM(sales)) OVER (PARTITION BY order_year ORDER BY order_month
                                   ROWS UNBOUNDED PRECEDING), 2)                        AS ytd_revenue
FROM vw_delivered_sales
GROUP BY order_year, order_month
ORDER BY order_month;

-- name: time_month_of_year
-- section: Time
-- title: Average revenue by calendar month across years (seasonal pattern), with each year's value
SELECT CAST(strftime('%m', order_date) AS INTEGER)                                     AS month_number,
       ROUND(SUM(CASE WHEN order_year = 2023 THEN sales END), 2)                         AS revenue_2023,
       ROUND(SUM(CASE WHEN order_year = 2024 THEN sales END), 2)                         AS revenue_2024,
       ROUND(SUM(CASE WHEN order_year = 2025 THEN sales END), 2)                         AS revenue_2025,
       ROUND(SUM(sales) / COUNT(DISTINCT order_year), 2)                                 AS avg_revenue,
       RANK() OVER (ORDER BY SUM(sales) DESC)                                            AS rank_by_total
FROM vw_delivered_sales
GROUP BY month_number
ORDER BY month_number;
