# Power BI Demonstration Script

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

> **Say this first, every time, before anyone asks.** "Power BI Desktop is a
> Windows application and was not available in the environment I built this in.
> The semantic model, all 84 DAX measures, the Power Query
> scripts, the theme and a full build guide are complete and validated —
> 48 of 48 measures match their SQL equivalents.
> The page layouts you'll see are **design mockups rendered from the real
> data**, not screenshots of a running report."
>
> Volunteering this costs you nothing. Being caught claiming a screenshot you
> do not have would cost the viva.

## The model behind every page

| Property | Value |
|---|---|
| Tables | 13 (star schema) |
| Relationships | 9, all one-to-many, single cross-filter direction |
| DAX measures | 84 in 10 display folders |
| Date table | Marked, one row per day, covering history and the forecast horizon |
| Measure validation | 48/48 match their SQL equivalents |
| Cross-surface consistency | 32/32 checks pass |

Every revenue measure carries an explicit delivered-lines filter, so the model
cannot silently report a different revenue definition from the pipeline:

```dax
Total Revenue =
CALCULATE ( SUM ( FactSales[Sales] ), FactSales[Is_Delivered] = TRUE () )
```

## Page by page

### Home / Navigation

- **Page purpose.** Entry point and navigation to the other eight pages
- **KPIs.** None — it is a landing page
- **Charts.** Navigation buttons, a description of each page, the synthetic-data notice
- **Filters.** None
- **Business question answered.** Where do I go for what?
- **Main insight.** The model is a governed starting point, not a free-for-all
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Executive Overview

- **Page purpose.** The monthly position in one screen for a manager with two minutes
- **KPIs.** Revenue {revenue}, profit {profit}, margin {margin}, orders {orders}, customers {cust_buy}, AOV {aov}
- **Charts.** Monthly revenue and profit line, revenue by region bar, revenue by category bar, revenue contribution by RFM segment, growth by year, concentration curve
- **Filters.** Date range, region, category, sub-category, segment, cluster
- **Business question answered.** How is the business performing and where is the revenue coming from?
- **Main insight.** Revenue grew {growth_2024} then {growth_2025} while margin rose to {margin_2025} — growth is not bought with margin
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Revenue Intelligence

- **Page purpose.** Decompose revenue and profit across every dimension
- **KPIs.** Revenue, profit, margin, AOV, units, lost value
- **Charts.** Revenue over time, by category and sub-category, by discount band, by payment method, delivered versus returned and cancelled
- **Filters.** Date range, category, discount band, payment method
- **Business question answered.** Which parts of the business earn, and which merely turn over?
- **Main insight.** The {disc0_band} discount band returns {disc0_margin} margin against {disc_hi_margin} in the {disc_hi_band} band
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Customer Intelligence

- **Page purpose.** Understand the customer base rather than the transaction base
- **KPIs.** Customers {cust_buy}, revenue per customer, repeat share, top-decile share
- **Charts.** Concentration curve, revenue-per-customer distribution, repeat versus single-purchase comparison, tenure against value, frequency bands
- **Filters.** Date range, region, segment, cluster
- **Business question answered.** How concentrated is the revenue, and where does repeat value come from?
- **Main insight.** Top 10% of customers produce {top10} of revenue; repeat customers are {repeat_cust} of the base and {repeat_rev} of revenue
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Customer Segmentation

- **Page purpose.** The two segmentation schemes side by side
- **KPIs.** Segments {rfm_segments}, clusters {k}, Champions share {champ_rev}, at-risk high-value count {at_risk}
- **Charts.** Customers and revenue by RFM segment, cluster profiles, the RFM-versus-cluster cross-tabulation, the at-risk high-value table
- **Filters.** Segment, cluster, recency band, value band
- **Business question answered.** Which customers matter, and which of them are going quiet?
- **Main insight.** Champions are {champ_cust} of customers but {champ_rev} of revenue; the two schemes agree at ARI {ari}
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Product Analytics

- **Page purpose.** Separate volume leaders from margin leaders
- **KPIs.** Revenue, profit and margin by category, sub-category and product; products flagged
- **Charts.** Category revenue versus profit, sub-category margin ranking, the product revenue–profit quadrant, top products by revenue and by profit
- **Filters.** Category, sub-category, date range
- **Business question answered.** Which products earn, and which only sell?
- **Main insight.** {top_cat} is {top_cat_rev} of revenue at {top_cat_margin} margin while {best_cat} earns {best_cat_margin}; {flagged} products flagged
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Regional Analytics

- **Page purpose.** Geography performance and the region × category margin test
- **KPIs.** Revenue, margin, customers and revenue per customer by region
- **Charts.** Revenue and profit by region, state map or bar, city ranking, the region × category margin matrix
- **Filters.** Region, state, category, date range
- **Business question answered.** Is any region or region–category pair underperforming on margin?
- **Main insight.** Revenue is evenly spread ({top_region} {top_region_share} to {small_region} {small_region_share}); {region_gaps} of {region_pairs} pairs sits more than 2 pp below national
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Prediction & Forecast

- **Page purpose.** The forward view, with its own accuracy shown beside it
- **KPIs.** Forecast total {fc_total}, backtest MAPE {fc_backtest}, prediction R² {pred_r2}, MAE {pred_mae}
- **Charts.** Historical revenue with the six-month forecast and intervals, actual versus predicted by quarter, predicted revenue by segment and cluster, the model metrics table
- **Filters.** Date range, segment, cluster
- **Business question answered.** What is revenue likely to be, and how much should we trust it?
- **Main insight.** Company forecast {fc_total} with an 80% interval {fc_low}–{fc_high}; individual prediction R² {pred_r2} is weak and shown as such
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Business Recommendations

- **Page purpose.** Turn the analysis into an action list
- **KPIs.** {pbi_recs} recommendations with their supporting metric and value
- **Charts.** Recommendation cards grouped by area, each with evidence, metric, value and analytical source
- **Filters.** Area (customer, product, regional, revenue)
- **Business question answered.** What should we actually do on Monday?
- **Main insight.** Protect the top decile ({top10} of revenue) and work the {at_risk}-customer inactive list
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.

### Customer Detail (drill-through)

- **Page purpose.** One customer's full history, reached by right-clicking any customer
- **KPIs.** That customer's revenue, profit, orders, recency, frequency, segment, cluster and estimated forward value
- **Charts.** Order history table, category mix, revenue over time for that customer
- **Filters.** Inherited from the page you drilled from
- **Business question answered.** Why is this specific customer in this segment?
- **Main insight.** Makes a segment assignment checkable by hand, which is the point of a rule-based scheme
- **Possible professor question.** *"Why this chart here?"* → Because the page
  answers one question and every visual on it serves that question.


## The five questions you will be asked

**"What is Power BI used for in your project?"**
It is the governed semantic layer. It takes the SQL views, joins them into a
13-table star schema, and exposes 84 conformed
measures so a business user can slice revenue by date, region, category,
segment or cluster without asking an analyst and without any risk of computing
revenue a different way.

**"Why did you use Power BI instead of Python?"**
They do different jobs, and I used both. Python fits the models and computes
the results; Power BI makes those results explorable by someone who does not
write code. Power BI cannot fit a K-Means model or run statsmodels, and Python
does not give a manager drag-and-drop slicing over a governed model.

**"What is the difference between Power BI and Streamlit?"**
Power BI is a dashboard over a semantic model — pre-computed measures,
self-service exploration. Streamlit is an application — it loads the actual
persisted `.pkl` models, runs predictions, accepts a file upload and returns a
download. Any page that needs a live model has to be Streamlit; any audience
that needs free-form slicing is better served by Power BI. The project ships
both deliberately.

**"How did you design the dashboard?"**
Following the published principles — high data-ink ratio, restrained colour, a
clear hierarchy with headline KPIs first, and one analytical purpose per page.
Each page answers one business question and every visual on it serves that
question. The honest caveat: design effectiveness can only be confirmed by
user testing, which was outside this internship's scope.

**"What KPIs did you select and why?"**
Six on the Executive Overview: revenue ₹6.01 Cr, profit ₹1.40 Cr,
margin 23.35%, orders 12,212, customers 1,984 and AOV
₹4,917.83. Revenue and profit because they are the outcome; margin because
revenue without margin is not growth; orders and customers because they
separate "more customers" from "bigger baskets"; and AOV because it is the
bridge between them. Every one is computed on delivered lines only.

## If asked to show it live

You cannot — and say so plainly rather than fumbling. Offer instead:

1. The design mockups in `outputs/screenshots/` (files 57–66).
2. `powerbi/dax/` — the actual measure library.
3. `powerbi/validation/` — the measure-by-measure comparison against SQL.
4. `powerbi/POWERBI_BUILD_GUIDE.md` — the build steps.
5. The Streamlit application, which **is** running, for anything interactive.
