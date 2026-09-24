# SQL Demonstration Script

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

```bash
sqlite3 data/customer_revenue_intelligence.db
.headers on
.mode column
```

The database: **11 tables, 2 views,
57 queries** (37 analysis +
20 business). All 56 referential and
business-rule checks and 20 data-quality checks pass.

---

## Query 1 — the reconciliation anchor

**Business question:** what is the headline performance of the delivered
revenue base, and does SQL agree with Python?

```sql
SELECT COUNT(DISTINCT o.order_id)                           AS orders,
       COUNT(DISTINCT o.customer_id)                        AS customers,
       ROUND(SUM(oi.sales), 2)                              AS revenue,
       ROUND(SUM(oi.net_profit), 2)                         AS profit,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct,
       ROUND(SUM(oi.sales) / COUNT(DISTINCT o.order_id), 2) AS aov
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

**Line by line.** `SELECT` lists the six measures. `COUNT(DISTINCT
o.order_id)` counts orders, not order lines — an order can carry several lines.
`SUM(oi.sales)` and `SUM(oi.net_profit)` aggregate at line level. The margin
multiplies by `100.0`, not `100`, to force float division in SQLite. `FROM
order_items` joined to `orders` gives every line its order and customer.
`WHERE oi.order_status = 'Delivered'` is the project's one revenue rule.

**Result type:** one row, six columns.

**Business interpretation:** ₹6.01 Cr revenue, ₹1.40 Cr profit,
23.35% margin, 12,212 orders, 1,984 customers, AOV
₹4,917.83 — identical to the Python pipeline and the DAX measures. **This is
the query to run live.**

---

## Query 2 — revenue concentration (window function + running total)

**Business question:** how much of revenue do the largest customers carry?

```sql
WITH cust AS (
    SELECT o.customer_id, SUM(oi.sales) AS revenue
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY o.customer_id
)
SELECT customer_id,
       ROUND(revenue, 2) AS revenue,
       ROW_NUMBER() OVER (ORDER BY revenue DESC) AS customer_rank,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY revenue DESC
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(revenue) OVER (), 2) AS cumulative_pct_of_revenue
FROM   cust
ORDER  BY revenue DESC
LIMIT  20;
```

**Line by line.** The `WITH cust AS (...)` CTE builds one row per customer —
readable, and reusable in the outer query. `ROW_NUMBER() OVER (ORDER BY revenue
DESC)` ranks customers without collapsing rows. The running total
`SUM(revenue) OVER (ORDER BY revenue DESC ROWS BETWEEN UNBOUNDED PRECEDING AND
CURRENT ROW)` accumulates down the ordered list, and dividing by `SUM(revenue)
OVER ()` — the grand total on every row — converts it to a cumulative share.

**Result type:** 20 rows, ranked.

**Business interpretation:** this query produces the project's central finding —
the top 10% of customers hold 45.39% of revenue and the top 20% hold
64.33%.

---

## Query 3 — year-over-year growth (LAG)

**Business question:** is the business growing, and is it buying that growth
with margin?

```sql
WITH yearly AS (
    SELECT strftime('%Y', o.order_date) AS yr,
           SUM(oi.sales)                AS revenue,
           SUM(oi.net_profit)           AS profit
    FROM   order_items oi
    JOIN   orders o ON o.order_id = oi.order_id
    WHERE  oi.order_status = 'Delivered'
    GROUP  BY yr
)
SELECT yr,
       ROUND(revenue, 2)                                  AS revenue,
       ROUND(100.0 * profit / revenue, 2)                 AS margin_pct,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY yr))
             / LAG(revenue) OVER (ORDER BY yr), 2)        AS yoy_growth_pct
FROM   yearly
ORDER  BY yr;
```

**Line by line.** `strftime('%Y', ...)` extracts the year — SQLite's date
function. `LAG(revenue) OVER (ORDER BY yr)` reads the previous year's revenue
on the current row, which is what makes a period-over-period calculation
possible without a self-join.

**Result type:** three rows, one per year.

**Business interpretation:** growth of 51.4% then
37.7% while margin rose from 22.65% to
23.90% — growth is not being bought with margin.

---

## Query 4 — revenue by RFM segment (JOIN to an analytical table)

**Business question:** how much revenue does each customer segment carry?

```sql
SELECT s.rfm_segment,
       COUNT(DISTINCT s.customer_id)                     AS customers,
       ROUND(SUM(oi.sales), 2)                           AS revenue,
       ROUND(100.0 * SUM(oi.sales)
             / (SELECT SUM(sales) FROM order_items
                WHERE order_status = 'Delivered'), 2)    AS pct_of_revenue
FROM   customer_rfm_segments s
JOIN   orders o       ON o.customer_id = s.customer_id
JOIN   order_items oi ON oi.order_id   = o.order_id
WHERE  oi.order_status = 'Delivered'
GROUP  BY s.rfm_segment
ORDER  BY revenue DESC;
```

**Line by line.** Two joins walk from the segment table to the customer's
orders to their order lines. The scalar **subquery** in the SELECT list
computes the grand total once, giving each segment its share. `GROUP BY` then
collapses to one row per segment.

**Result type:** 11 rows.

**Business interpretation:** Champions hold 53.83% of revenue on
16.84% of customers; At Risk holds 11.26%.

---

## Query 5 — inactive high-value customers (HAVING + CASE)

**Business question:** which valuable customers have gone quiet?

```sql
SELECT o.customer_id,
       ROUND(SUM(oi.sales), 2)                       AS lifetime_revenue,
       MAX(o.order_date)                             AS last_order_date,
       CAST(julianday('2026-01-01') - julianday(MAX(o.order_date)) AS INT)
                                                     AS recency_days,
       CASE WHEN julianday('2026-01-01') - julianday(MAX(o.order_date)) >= 180
            THEN 'Inactive 180+ days' ELSE 'Active' END AS status
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered'
GROUP  BY o.customer_id
HAVING SUM(oi.sales) > (SELECT AVG(total) FROM
          (SELECT SUM(sales) AS total FROM order_items oi2
           JOIN orders o2 ON o2.order_id = oi2.order_id
           WHERE oi2.order_status = 'Delivered'
           GROUP BY o2.customer_id))
   AND julianday('2026-01-01') - julianday(MAX(o.order_date)) >= 180
ORDER  BY lifetime_revenue DESC;
```

**Line by line.** `MAX(o.order_date)` gives the last purchase per customer.
`julianday()` differences two dates in days — SQLite's date arithmetic.
`CASE WHEN` labels the row. `HAVING` filters **after** aggregation, which
`WHERE` cannot do: it keeps customers whose lifetime revenue exceeds the base
average — computed by a nested subquery — and who have been silent 180 days or
more.

**Result type:** the working list.

**Business interpretation:** this is the logic behind the 52
high-value inactive customers holding ₹26.51 L. Note the reference
date 2026-01-01 is fixed, not `date('now')` — the data ends at
31 December 2025.

---

## Query 6 — discount band against margin (CASE WHEN banding)

**Business question:** what does discounting cost in margin?

```sql
SELECT CASE WHEN oi.discount = 0             THEN '0%'
            WHEN oi.discount <= 0.10         THEN '1-10%'
            WHEN oi.discount <= 0.20         THEN '11-20%'
            ELSE '20%+' END                            AS discount_band,
       COUNT(*)                                        AS order_lines,
       ROUND(SUM(oi.sales), 2)                         AS revenue,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
WHERE  oi.order_status = 'Delivered'
GROUP  BY discount_band
ORDER  BY discount_band;
```

**Business interpretation:** the 0% band returns
29.31% margin against 20.43% in the
31-40% band. Say the caveat out loud: this is an **association**
measured on observed orders, not proof that discounting causes the gap.

---

## SQL concepts, in the project's own terms

| Concept | What it does | Where it is used here |
|---|---|---|
| `SELECT` | Chooses the columns returned | Every query |
| `WHERE` | Filters rows **before** grouping | The revenue rule: `order_status = 'Delivered'` |
| `GROUP BY` | Collapses rows into groups for aggregation | 54 queries |
| `HAVING` | Filters **after** aggregation | 2 queries — e.g. high-value inactive customers |
| `ORDER BY` | Sorts the result | Every top-N query |
| `JOIN` / `INNER JOIN` | Keeps only matching rows | 18 queries — `orders` ↔ `order_items` is the spine |
| `LEFT JOIN` | Keeps all left-table rows | 7 queries — keeps products with no delivered sales, so the denominator is honest |
| `CASE WHEN` | Conditional logic inside a query | 19 queries — discount bands, age bands, conditional counts |
| Aggregates | `SUM`, `AVG`, `COUNT`, `MIN`, `MAX` | Revenue is `SUM(sales)`; AOV is `SUM(sales)/COUNT(DISTINCT order_id)` |
| Subqueries | A query nested inside another | 10 queries — comparing a customer against the base average |
| CTEs (`WITH`) | A named temporary result | 27 queries — readability and reuse |
| Window functions | Compute across related rows without collapsing them | 35 queries — the most-used advanced technique here |
| `ROW_NUMBER` / `RANK` | Sequential or tied ranking | 22 queries — top customers and products |
| Running totals | `SUM(...) OVER (ORDER BY ... ROWS BETWEEN ...)` | 4 queries — the concentration curve |
| `SUM() OVER ()` | Grand total on every row | 18 queries — percentage-of-total columns |
| `LAG` / `LEAD` | Previous or next row in the window | 5 queries — YoY and MoM growth |
| Date functions | `strftime`, `julianday` | 7 queries — year, month, quarter, recency |
| `UNION ALL` | Stacks two result sets | 1 query (BQ10) |

## If asked to run something unplanned

Open `sql/analysis_queries.sql` or `sql/business_queries.sql` — every query is
there, commented with the business question it answers. Running one you have
not rehearsed is fine; the file is the evidence that all
57 exist.
