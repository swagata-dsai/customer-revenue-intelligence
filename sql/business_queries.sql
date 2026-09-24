-- =============================================================================
-- business_queries.sql — Customer Revenue Intelligence (SYNTHETIC DATA)
-- 20 business questions answered directly from data/customer_revenue_intelligence.db
-- =============================================================================
-- Each block documents:
--   question        the business question
--   purpose         the expected analytical purpose (what decision it informs)
--   interpretation  how to read the result (no result values are written here - they come from running the SQL)
-- Revenue rule: Delivered lines only (vw_delivered_sales). Customers are shown by customer_id only.
-- Results: outputs/tables/sql/<name>.csv (written by src/sql_analytics.py)
-- =============================================================================


-- name: BQ01
-- question: Which customers generate the highest revenue?
-- purpose: Identify the accounts the business depends on most, for key-account management.
-- interpretation: Read revenue_rank and pct_of_total_revenue; compare the top 10's combined share with BQ10 to judge dependence on a few customers. rfm_segment / cluster show whether they are still active.
-- techniques: CTE, window RANK, window SUM for share, LEFT JOIN to analytics tables
WITH c AS (
    SELECT customer_id, SUM(sales) AS revenue, SUM(profit) AS profit, COUNT(DISTINCT order_id) AS orders,
           MAX(order_date) AS last_order
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT RANK() OVER (ORDER BY c.revenue DESC)                        AS revenue_rank,
       c.customer_id,
       ROUND(c.revenue, 2)                                          AS revenue,
       ROUND(100.0 * c.revenue / SUM(c.revenue) OVER (), 3)         AS pct_of_total_revenue,
       ROUND(c.profit, 2)                                           AS profit,
       c.orders, c.last_order,
       r.rfm_segment, m.cluster_label
FROM c
LEFT JOIN customer_rfm r      ON r.customer_id = c.customer_id
LEFT JOIN customer_segments s ON s.customer_id = c.customer_id
LEFT JOIN ml_clusters m       ON m.cluster_id  = s.cluster_id
ORDER BY c.revenue DESC
LIMIT 10;

-- name: BQ02
-- question: Which customer segments contribute the most revenue?
-- purpose: Size each RFM segment's commercial weight to prioritise segment strategies.
-- interpretation: Compare revenue_contribution_pct with customer_pct - segments whose revenue share far exceeds their customer share are high-value; the reverse indicates low-value or inactive segments.
-- techniques: CTE, INNER JOIN, window SUM for percentage contribution, RANK
WITH c AS (SELECT customer_id, SUM(sales) AS revenue FROM vw_delivered_sales GROUP BY customer_id)
SELECT RANK() OVER (ORDER BY SUM(c.revenue) DESC)                   AS revenue_rank,
       r.rfm_segment,
       COUNT(*)                                                     AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)           AS customer_pct,
       ROUND(SUM(c.revenue), 2)                                     AS revenue,
       ROUND(100.0 * SUM(c.revenue) / SUM(SUM(c.revenue)) OVER (), 2) AS revenue_contribution_pct,
       ROUND(SUM(c.revenue) / COUNT(*), 2)                          AS revenue_per_customer
FROM customer_rfm r
JOIN c ON c.customer_id = r.customer_id
GROUP BY r.rfm_segment
ORDER BY revenue DESC;

-- name: BQ03
-- question: Which products generate high revenue but relatively low profit?
-- purpose: Find revenue drivers that contribute little profit (pricing, cost or discount review).
-- interpretation: Products in the top revenue quartile whose margin is in the bottom margin quartile; margin_gap_vs_category shows how far below their own category they sit.
-- techniques: CTE, window NTILE, subquery for category margin, CASE-free filter on derived quartiles
WITH p AS (
    SELECT product_id, product_name, category, SUM(sales) AS revenue, SUM(profit) AS profit,
           SUM(profit) / SUM(sales) AS margin
    FROM vw_delivered_sales
    GROUP BY product_id, product_name, category
),
q AS (
    SELECT *, NTILE(4) OVER (ORDER BY revenue DESC) AS revenue_quartile,
              NTILE(4) OVER (ORDER BY margin ASC)   AS margin_quartile
    FROM p
)
SELECT product_id, product_name, category,
       ROUND(revenue, 2) AS revenue, ROUND(profit, 2) AS profit,
       ROUND(100.0 * margin, 2)                                               AS profit_margin_pct,
       ROUND(100.0 * (margin - (SELECT SUM(profit) / SUM(sales) FROM vw_delivered_sales v
                                WHERE v.category = q.category)), 2)          AS margin_gap_vs_category_pp
FROM q
WHERE revenue_quartile = 1 AND margin_quartile = 1
ORDER BY revenue DESC;

-- name: BQ04
-- question: Which categories have the highest profit margins?
-- purpose: Understand where each rupee of revenue earns the most profit (mix and promotion planning).
-- interpretation: Rank by profit_margin_pct but read it together with revenue_share_pct: a high-margin category with a small share has limited absolute impact.
-- techniques: aggregation, window SUM for share, RANK
SELECT RANK() OVER (ORDER BY SUM(profit) / SUM(sales) DESC)          AS margin_rank,
       category,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                    AS profit_margin_pct,
       ROUND(SUM(profit), 2)                                         AS profit,
       ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 2)        AS revenue_share_pct,
       ROUND(100.0 * SUM(profit) / SUM(SUM(profit)) OVER (), 2)      AS profit_share_pct
FROM vw_delivered_sales
GROUP BY category
ORDER BY margin_rank;

-- name: BQ05
-- question: Which regions generate the highest revenue?
-- purpose: Allocate regional sales and marketing effort.
-- interpretation: Revenue share shows scale; revenue_per_customer and AOV show whether a region is large because of more customers or higher spend per customer.
-- techniques: aggregation, window SUM, RANK
SELECT RANK() OVER (ORDER BY SUM(sales) DESC)                        AS revenue_rank,
       region,
       ROUND(SUM(sales), 2)                                          AS revenue,
       ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 2)        AS revenue_share_pct,
       COUNT(DISTINCT customer_id)                                   AS customers,
       ROUND(SUM(sales) / COUNT(DISTINCT customer_id), 2)            AS revenue_per_customer,
       ROUND(SUM(sales) / COUNT(DISTINCT order_id), 2)               AS average_order_value,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                    AS profit_margin_pct
FROM vw_delivered_sales
GROUP BY region
ORDER BY revenue_rank;

-- name: BQ06
-- question: Which customers have high historical value but low recent activity?
-- purpose: Build a re-engagement list of valuable customers who have gone quiet (potentially at-risk, not churned).
-- interpretation: High historical value = top 20% historical profit (Step 7 flag); low recent activity = no purchase for >= 180 days before the reference date (computed here). Sorted by lifetime revenue; estimated_12m_profit is a model estimate, not a promise.
-- techniques: CTE, date functions (julianday, date modifiers), scalar subquery for reference date, INNER JOIN
WITH ref AS (SELECT date(MAX(order_date), '+1 day') AS ref_date FROM orders),
last_buy AS (
    SELECT customer_id, MAX(order_date) AS last_order, SUM(sales) AS revenue, COUNT(DISTINCT order_id) AS orders
    FROM vw_delivered_sales
    GROUP BY customer_id
)
SELECT l.customer_id,
       l.last_order,
       CAST(julianday((SELECT ref_date FROM ref)) - julianday(l.last_order) AS INTEGER) AS days_since_last_order,
       ROUND(l.revenue, 2)                                    AS lifetime_revenue,
       ROUND(v.historical_profit_clv, 2)                      AS historical_profit,
       l.orders,
       r.rfm_segment,
       ROUND(v.estimated_12m_future_profit, 2)                AS estimated_12m_profit
FROM last_buy l
JOIN customer_value v ON v.customer_id = l.customer_id
JOIN customer_rfm r   ON r.customer_id = l.customer_id
WHERE v.high_historical_value = 1
  AND julianday((SELECT ref_date FROM ref)) - julianday(l.last_order) >= 180
ORDER BY l.revenue DESC;

-- name: BQ07
-- question: Which products have high sales volume but low profitability?
-- purpose: Flag popular products whose unit economics may need attention (price, cost, discount).
-- interpretation: Top-quartile units sold AND bottom-half margin. Popular but thin-margin items can still be strategic (traffic drivers); this is a list for review, not a verdict.
-- techniques: CTE, NTILE, window functions, filter on derived columns
WITH p AS (
    SELECT product_id, product_name, category, SUM(quantity) AS units, SUM(sales) AS revenue,
           SUM(profit) / SUM(sales) AS margin, AVG(discount) AS avg_discount
    FROM vw_delivered_sales
    GROUP BY product_id, product_name, category
),
q AS (
    SELECT *, NTILE(4) OVER (ORDER BY units DESC) AS volume_quartile,
              NTILE(2) OVER (ORDER BY margin ASC) AS margin_half
    FROM p
)
SELECT product_id, product_name, category, units,
       ROUND(revenue, 2)                AS revenue,
       ROUND(100.0 * margin, 2)         AS profit_margin_pct,
       ROUND(100.0 * avg_discount, 2)   AS avg_discount_pct
FROM q
WHERE volume_quartile = 1 AND margin_half = 1
ORDER BY units DESC;

-- name: BQ08
-- question: How does discount level relate to profitability?
-- purpose: Inform discount policy by showing margin and loss-making lines at each discount level, within category.
-- interpretation: Compare margin across discount bands WITHIN each category (the category mix differs by band). A lower margin at higher discounts is an association; it does not prove discounts cause lower profit.
-- techniques: CASE WHEN banding, aggregation, window partition for within-category comparison
SELECT category,
       CASE WHEN discount = 0 THEN '0%' WHEN discount <= 0.10 THEN '1-10%'
            WHEN discount <= 0.20 THEN '11-20%' ELSE '21-40%' END                   AS discount_band,
       COUNT(*)                                                                    AS order_lines,
       ROUND(SUM(sales), 2)                                                        AS revenue,
       ROUND(100.0 * SUM(profit) / SUM(sales), 2)                                  AS profit_margin_pct,
       ROUND(100.0 * SUM(profit) / SUM(sales)
             - MAX(100.0 * SUM(profit) / SUM(sales)) OVER (PARTITION BY category), 2) AS margin_vs_best_band_pp,
       ROUND(100.0 * SUM(CASE WHEN profit < 0 THEN 1 ELSE 0 END) / COUNT(*), 2)     AS loss_making_lines_pct
FROM vw_delivered_sales
GROUP BY category, discount_band
ORDER BY category, MIN(discount);

-- name: BQ09
-- question: Which months generate the highest revenue?
-- purpose: Plan inventory, staffing and campaigns around recurring peaks.
-- interpretation: rank_in_year shows whether the same calendar month leads every year (a recurring peak) or only once (a one-off).
-- techniques: CTE, window RANK partitioned by year, date functions (strftime)
WITH m AS (
    SELECT order_year, CAST(strftime('%m', order_date) AS INTEGER) AS month_number, order_month,
           SUM(sales) AS revenue
    FROM vw_delivered_sales
    GROUP BY order_year, month_number, order_month
), ranked AS (
    SELECT order_year, order_month, revenue,
           RANK() OVER (PARTITION BY order_year ORDER BY revenue DESC)                     AS rank_in_year,
           100.0 * revenue / SUM(revenue) OVER (PARTITION BY order_year)                   AS pct_of_year_revenue
    FROM m
)
SELECT order_year, order_month, ROUND(revenue, 2) AS revenue, rank_in_year,
       ROUND(pct_of_year_revenue, 2) AS pct_of_year_revenue
FROM ranked
WHERE rank_in_year <= 3                -- top 3 months of each year
ORDER BY order_year, rank_in_year;

-- name: BQ10
-- question: What percentage of total revenue comes from high-value customers?
-- purpose: Quantify revenue concentration for risk and retention planning.
-- interpretation: Two definitions are shown side by side - top 20% of customers by revenue (NTILE) and the Step 7 'high historical value' flag (top 20% by profit). Similar shares mean the conclusion does not depend on the definition.
-- techniques: CTE, NTILE, CASE WHEN, UNION ALL, scalar subquery for the total
WITH c AS (SELECT customer_id, SUM(sales) AS revenue FROM vw_delivered_sales GROUP BY customer_id),
q AS (SELECT customer_id, revenue, NTILE(5) OVER (ORDER BY revenue DESC) AS revenue_quintile FROM c)
SELECT 'Top 20% of customers by revenue'                             AS definition,
       SUM(CASE WHEN revenue_quintile = 1 THEN 1 ELSE 0 END)         AS customers,
       ROUND(100.0 * SUM(CASE WHEN revenue_quintile = 1 THEN revenue ELSE 0 END) / SUM(revenue), 2) AS pct_of_revenue
FROM q
UNION ALL
SELECT 'Step 7 high historical value (top 20% by profit)',
       SUM(v.high_historical_value),
       ROUND(100.0 * SUM(CASE WHEN v.high_historical_value = 1 THEN c.revenue ELSE 0 END)
             / (SELECT SUM(revenue) FROM c), 2)
FROM customer_value v
JOIN c ON c.customer_id = v.customer_id;

-- name: BQ11
-- question: Which ML cluster earns the most profit per customer, and how much of total profit does each hold?
-- purpose: Connect the Step 6 segmentation to profitability for resource allocation.
-- interpretation: profit_per_customer shows intensity, profit_share_pct shows weight; a cluster can be important because it is large rather than rich.
-- techniques: INNER JOIN across three tables, aggregation, window SUM
SELECT m.cluster_label,
       COUNT(DISTINCT s.customer_id)                                          AS customers,
       ROUND(SUM(d.profit), 2)                                                AS profit,
       ROUND(SUM(d.profit) / COUNT(DISTINCT s.customer_id), 2)                AS profit_per_customer,
       ROUND(100.0 * SUM(d.profit) / SUM(SUM(d.profit)) OVER (), 2)           AS profit_share_pct,
       ROUND(100.0 * SUM(d.profit) / SUM(d.sales), 2)                         AS profit_margin_pct
FROM customer_segments s
JOIN ml_clusters m        ON m.cluster_id  = s.cluster_id
JOIN vw_delivered_sales d ON d.customer_id = s.customer_id
GROUP BY m.cluster_id, m.cluster_label
ORDER BY profit_per_customer DESC;

-- name: BQ12
-- question: How much revenue comes from repeat customers versus single-purchase customers?
-- purpose: Show the value of the second purchase for onboarding and retention.
-- interpretation: Compare pct_of_revenue with pct_of_customers for each group.
-- techniques: CTE, CASE WHEN, window SUM
WITH c AS (
    SELECT customer_id, COUNT(DISTINCT order_id) AS orders, SUM(sales) AS revenue
    FROM vw_delivered_sales GROUP BY customer_id
)
SELECT CASE WHEN orders = 1 THEN 'Single purchase' ELSE 'Repeat (2+ orders)' END   AS customer_group,
       COUNT(*)                                                                     AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                           AS pct_of_customers,
       ROUND(SUM(revenue), 2)                                                       AS revenue,
       ROUND(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 2)                   AS pct_of_revenue,
       ROUND(AVG(revenue), 2)                                                       AS avg_revenue_per_customer
FROM c
GROUP BY customer_group;

-- name: BQ13
-- question: Which payment methods have the highest order value and the highest return/cancellation rates?
-- purpose: Inform checkout and payment-policy decisions (e.g. COD handling).
-- interpretation: A payment method with a high return/cancel rate is associated with lost revenue; causes (customer mix, product mix) need further investigation.
-- techniques: LEFT JOIN, CASE WHEN inside aggregates, conditional ratios
SELECT o.payment_method,
       COUNT(DISTINCT o.order_id)                                                              AS orders,
       ROUND(SUM(CASE WHEN oi.order_status = 'Delivered' THEN oi.sales END)
             / COUNT(DISTINCT CASE WHEN oi.order_status = 'Delivered' THEN o.order_id END), 2) AS delivered_aov,
       ROUND(100.0 * SUM(CASE WHEN oi.order_status = 'Returned'  THEN 1 ELSE 0 END) / COUNT(*), 2) AS returned_lines_pct,
       ROUND(100.0 * SUM(CASE WHEN oi.order_status = 'Cancelled' THEN 1 ELSE 0 END) / COUNT(*), 2) AS cancelled_lines_pct
FROM orders o
LEFT JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY o.payment_method
ORDER BY orders DESC;

-- name: BQ14
-- question: Which categories lose the most value to returns and cancellations?
-- purpose: Target return-reduction and quality initiatives where the lost value is largest.
-- interpretation: lost_value is the booked value (qty x price x (1 - discount)) of Returned + Cancelled lines; compare lost_pct_of_booked across categories.
-- techniques: INNER JOIN, CASE WHEN in aggregates, derived percentages
SELECT p.category,
       ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2)                               AS booked_value,
       ROUND(SUM(CASE WHEN oi.order_status <> 'Delivered'
                      THEN oi.quantity * oi.unit_price * (1 - oi.discount) ELSE 0 END), 2)         AS lost_value,
       ROUND(100.0 * SUM(CASE WHEN oi.order_status <> 'Delivered'
                              THEN oi.quantity * oi.unit_price * (1 - oi.discount) ELSE 0 END)
             / SUM(oi.quantity * oi.unit_price * (1 - oi.discount)), 2)                            AS lost_pct_of_booked,
       ROUND(100.0 * SUM(CASE WHEN oi.order_status = 'Returned' THEN 1 ELSE 0 END) / COUNT(*), 2)   AS returned_lines_pct
FROM order_items oi
JOIN products p ON p.product_id = oi.product_id
GROUP BY p.category
ORDER BY lost_value DESC;

-- name: BQ15
-- question: How has the active customer base changed year over year (retained, new and returning customers)?
-- purpose: Separate growth from acquisition vs retention.
-- interpretation: retained = active this year and last year; new = first ever purchase this year; reactivated = active this year, not last year, but bought before. retention_rate_pct = retained / active last year.
-- techniques: CTE, self-join (LEFT JOIN on year - 1), CASE WHEN, LAG
WITH act AS (SELECT DISTINCT customer_id, order_year FROM vw_delivered_sales),
first_year AS (SELECT customer_id, MIN(order_year) AS first_year FROM act GROUP BY customer_id),
cls AS (
    SELECT a.order_year, a.customer_id,
           CASE WHEN f.first_year = a.order_year THEN 'new'
                WHEN prev.customer_id IS NOT NULL THEN 'retained'
                ELSE 'reactivated' END AS status
    FROM act a
    JOIN first_year f ON f.customer_id = a.customer_id
    LEFT JOIN act prev ON prev.customer_id = a.customer_id AND prev.order_year = a.order_year - 1
),
y AS (
    SELECT order_year, COUNT(*) AS active_customers,
           SUM(status = 'new') AS new_customers, SUM(status = 'retained') AS retained_customers,
           SUM(status = 'reactivated') AS reactivated_customers
    FROM cls GROUP BY order_year
)
SELECT order_year, active_customers, new_customers, retained_customers, reactivated_customers,
       ROUND(100.0 * retained_customers / LAG(active_customers) OVER (ORDER BY order_year), 2) AS retention_rate_pct
FROM y
ORDER BY order_year;

-- name: BQ16
-- question: Which region-category combinations have margins well below the category's national margin?
-- purpose: Find local pricing, discount or cost issues worth investigating.
-- interpretation: margin_gap_pp < 0 means the region earns a lower margin on that category than the country as a whole; flag_below_2pp = 1 marks gaps of more than 2 percentage points (all 30 combinations are listed, worst first, so an empty flag column is itself the answer).
-- techniques: CTE, INNER JOIN of two aggregates, derived gap, filter
WITH rc AS (
    SELECT region, category, SUM(sales) AS revenue, SUM(profit) / SUM(sales) AS margin
    FROM vw_delivered_sales GROUP BY region, category
),
c AS (SELECT category, SUM(profit) / SUM(sales) AS national_margin FROM vw_delivered_sales GROUP BY category)
SELECT rc.region, rc.category,
       ROUND(rc.revenue, 2)                                AS revenue,
       ROUND(100.0 * rc.margin, 2)                         AS region_margin_pct,
       ROUND(100.0 * c.national_margin, 2)                 AS national_margin_pct,
       ROUND(100.0 * (rc.margin - c.national_margin), 2)   AS margin_gap_pp,
       CASE WHEN rc.margin - c.national_margin < -0.02 THEN 1 ELSE 0 END AS flag_below_2pp
FROM rc
JOIN c ON c.category = rc.category
ORDER BY margin_gap_pp;

-- name: BQ17
-- question: How long do repeat customers typically wait between orders?
-- purpose: Set sensible timing for reminder or re-engagement campaigns.
-- interpretation: gap statistics over all consecutive order pairs; the 75th-90th percentile gap is a reasonable point to start worrying about inactivity (Step 7 used 180 days).
-- techniques: CTE, LAG window over each customer's orders, julianday, NTILE for percentiles
WITH o AS (
    SELECT DISTINCT customer_id, order_id, order_date FROM vw_delivered_sales
),
g AS (
    SELECT customer_id,
           julianday(order_date) - julianday(LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date, order_id)) AS gap_days
    FROM o
),
p AS (SELECT gap_days, NTILE(20) OVER (ORDER BY gap_days) AS vigintile FROM g WHERE gap_days IS NOT NULL)
SELECT COUNT(*)                                         AS repeat_intervals,
       ROUND(AVG(gap_days), 1)                          AS mean_gap_days,
       MAX(CASE WHEN vigintile = 5  THEN gap_days END)  AS p25_gap_days,
       MAX(CASE WHEN vigintile = 10 THEN gap_days END)  AS median_gap_days,
       MAX(CASE WHEN vigintile = 15 THEN gap_days END)  AS p75_gap_days,
       MAX(CASE WHEN vigintile = 18 THEN gap_days END)  AS p90_gap_days
FROM p;

-- name: BQ18
-- question: Which customers are estimated to be most valuable next year but are not yet Champions?
-- purpose: Find growth candidates for nurturing programmes before they become top customers.
-- interpretation: Ranked by the Step 7 estimated next-12-month profit (a model estimate under stated assumptions, not a guarantee), excluding customers already in the Champions segment.
-- techniques: INNER JOIN, subquery filter (NOT IN), ranking window
SELECT RANK() OVER (ORDER BY v.estimated_12m_future_profit DESC)     AS estimate_rank,
       v.customer_id, r.rfm_segment, m.cluster_label,
       ROUND(v.estimated_12m_future_profit, 2)                       AS estimated_12m_profit,
       ROUND(v.historical_profit_clv, 2)                             AS historical_profit,
       r.recency_days, r.frequency_orders
FROM customer_value v
JOIN customer_rfm r      ON r.customer_id = v.customer_id
JOIN customer_segments s ON s.customer_id = v.customer_id
JOIN ml_clusters m       ON m.cluster_id  = s.cluster_id
WHERE v.customer_id NOT IN (SELECT customer_id FROM customer_rfm WHERE rfm_segment = 'Champions')
ORDER BY v.estimated_12m_future_profit DESC
LIMIT 20;

-- name: BQ19
-- question: How concentrated is revenue across products?
-- purpose: Assess dependence on a few products (supply and assortment risk).
-- interpretation: cumulative_pct shows how many products make up a given share of revenue.
-- techniques: CTE, ROW_NUMBER, running total with window frame, percentage contribution
WITH p AS (SELECT product_id, product_name, category, SUM(sales) AS revenue FROM vw_delivered_sales
           GROUP BY product_id, product_name, category)
SELECT ROW_NUMBER() OVER (ORDER BY revenue DESC)                                       AS product_rank,
       product_id, product_name, category,
       ROUND(revenue, 2)                                                               AS revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 2)                                AS pct_of_revenue,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)
             / SUM(revenue) OVER (), 2)                                                AS cumulative_pct
FROM p
ORDER BY product_rank
LIMIT 20;

-- name: BQ20
-- question: How did the Step 9 forecasts compare with actual revenue, and what do they imply for the next six months?
-- purpose: Connect the forecasting output to the database so planners can query forecast vs actual in one place.
-- interpretation: For evaluation months, error_pct = (forecast - actual) / actual; future months have no actual yet and show the prediction interval. Forecasts are estimates, not targets.
-- techniques: LEFT JOIN of a table to an aggregate, CASE WHEN, derived error
SELECT f.month, f.record_type,
       ROUND(COALESCE(f.actual_revenue, a.revenue), 2)                                     AS actual_revenue,
       ROUND(f.forecast_revenue, 2)                                                        AS forecast_revenue,
       CASE WHEN f.forecast_revenue IS NOT NULL AND COALESCE(f.actual_revenue, a.revenue) IS NOT NULL
            THEN ROUND(100.0 * (f.forecast_revenue - COALESCE(f.actual_revenue, a.revenue))
                       / COALESCE(f.actual_revenue, a.revenue), 2) END                     AS error_pct,
       ROUND(f.lower_95, 2) AS lower_95, ROUND(f.upper_95, 2) AS upper_95
FROM revenue_forecasts f
LEFT JOIN (SELECT order_month, SUM(sales) AS revenue FROM vw_delivered_sales GROUP BY order_month) a
       ON a.order_month = f.month
WHERE f.record_type <> 'Historical actual'
ORDER BY f.month, f.record_type;
