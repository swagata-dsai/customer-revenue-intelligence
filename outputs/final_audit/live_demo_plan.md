# Live Demonstration Plan

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

A 15-minute demonstration, timed. If you are given 10 minutes, drop sections
6, 11 and 14 and shorten 5 — the compressed running order is at the end.

**Before you start:** open a terminal in the project folder with the virtual
environment active, run `streamlit run app.py` and leave it running in a
browser tab; open the report PDF in a second tab; open
`outputs/screenshots/` in a file browser as the fallback.

---

### 1. Project Introduction — 45 s

- **Open:** PPT slide 1, or just talk.
- **Show:** the project title.
- **Explain:** who you are, where the internship was, and that the platform
  takes retail transaction data from raw file to business decision.
- **Result to mention:** the platform spans 41 Python modules and
  is verified by 135 automated checks.
- **Likely question:** *"What was your role?"* → Say plainly what you built.

### 2. Business Problem — 1 min

- **Open:** PPT slide 2.
- **Show:** the four gaps.
- **Explain:** aggregate reporting hides the customer; value and activity get
  treated as one thing; planning is backward-looking; analysis never reaches
  the decision-maker.
- **Result to mention:** the top 20% of customers produce 64.33% of
  revenue — a fact monthly totals cannot reveal.
- **Likely question:** *"Why not just improve the reports?"* → Because the
  decisions are taken at customer level.

### 3. Dataset — 1 min

- **Open:** `outputs/screenshots/01_raw_dataset_preview.png` and
  `02_clean_dataset_preview.png`.
- **Show:** the raw extract beside the cleaned dataset.
- **Explain:** synthetic, generated with seed 42;
  18,819 raw lines over 23 columns covering
  1,984 purchasing customers, 61 products and
  5 regions from 01 January 2023 to 31 December 2025.
- **Result to mention:** say "synthetic" **before** you are asked.
- **Likely question:** *"Why synthetic?"* → No confidentiality constraint,
  full reproducibility, and a known ground truth to audit cleaning against.

### 4. Data Cleaning — 1 min

- **Open:** `outputs/screenshots/01_raw_dataset_preview.png` beside
  `02_clean_dataset_preview.png`, then `03_data_quality_missing_before.png`,
  `04_..._after.png` and `05_data_quality_issue_summary.png`.
- **Show:** the two previews side by side — this is the most persuasive 20
  seconds of the demo, because the fixes are visible in row 2: the date
  `01/01/2023` becomes `2023-01-01`, and the city `Bombay` is standardised to
  `Mumbai`. Point at them.
- **Explain:** every rule is evaluated on the raw data, failing rows logged,
  treatment applied, rule re-evaluated.
- **Result to mention:** 941 rows failed at least one rule
  before treatment; **zero** rules fail after. 149 duplicates removed;
  28 engineered columns added.
- **Likely question:** *"How did you handle missing values?"* → By column, by
  meaning; some recovered by arithmetic; nothing dropped silently.

### 5. EDA — 2 min

- **Open:** Streamlit → **Executive Overview**, then **Revenue Intelligence**.
- **Show:** the KPI row, then the monthly revenue trend, then category revenue
  versus profit.
- **Explain:** each chart answers a business question.
- **Results to mention:** ₹6.01 Cr delivered revenue at 23.35%
  margin, 12,212 orders, AOV ₹4,917.83; growth 51.4% then
  37.7% while margin rose to 23.90% — growth is not
  bought with margin; Electronics is 50.10% of revenue but only
  23.29% of profit, while Beauty earns
  46.49%.
- **Likely question:** *"Is October seasonality?"* → An observed regularity in
  all three years; the formal test on 36 observations does not
  confirm it.

### 6. RFM Analysis — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation**, RFM view.
- **Show:** the segment distribution and the revenue contribution chart.
- **Explain:** recency, frequency and monetary value scored 1–5 on quintiles at
  reference date 2026-01-01, then fixed rules into
  11 segments.
- **Results to mention:** 1,984 customers scored; Champions are
  334 customers (16.84%) holding 53.83% of
  revenue; At Risk holds 11.26%.
- **Likely question:** *"Why that reference date?"* → It is the latest order
  date plus one day; today's real date would make everyone look inactive.

### 7. Customer Segmentation (K-Means) — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation**, cluster view; keep
  `outputs/screenshots/26_kmeans_elbow_curve.png` and
  `27_kmeans_silhouette_scores.png` ready.
- **Show:** the cluster profile and the PCA projection.
- **Explain:** the same three features, log1p → scaling, K chosen by **three
  rules fixed in advance** — K ≥ 3, no cluster under
  5%, stability ARI ≥ 0.90 — then highest silhouette.
- **Results to mention:** K = 4, silhouette 0.3534,
  stability 0.95; cluster 0 (High-Value, Active) is 18.35% of
  customers and 55.67% of revenue; agreement with RFM, ARI 0.3952.
- **Likely question:** *"Your silhouette is low."* → Agreed, the base is a
  continuum; what makes it usable is the profile difference and the
  independent agreement with RFM.

### 8. Customer Lifetime Value — 1 min 30 s

- **Open:** Streamlit → **Customer Segmentation** (value view) or
  `outputs/screenshots/37_clv_by_rfm_segment.png`.
- **Show:** historical value beside estimated forward value.
- **Explain:** two quantities, never added. Historical is measured; forward is
  a random forest trained out of time.
- **Results to mention:** historical ₹1.40 Cr of profit, mean
  ₹7,068 against median ₹3,893; model R² 0.2705 but
  Spearman 0.4869 — it ranks well, it does not predict levels;
  **52 high-value customers inactive 180+ days holding
  ₹26.51 L**.
- **Likely question:** *"Is this predictive CLV?"* → The forward figure is an
  estimate with stated error; the historical figure is measured. They are
  reported separately.

### 9. Revenue Prediction — 1 min 30 s

- **Open:** Streamlit → **Revenue Prediction**.
- **Show:** the predictions **and** the accuracy panel beside them.
- **Explain:** target is Next_Quarter_Revenue = Delivered Sales (Rs) in the 3 months after the cutoff; a 10,393-row
  customer-quarter panel, 24 features all computed before the
  cutoff, chronological split, leakage audited.
- **Results to mention:** test MAE ₹5,658, R² 0.0557 — **weak,
  and say so**. The naive baseline scores R² -0.5700. Cause:
  53.0% of customer-quarters are zero. Total bias 1.12%,
  so it is usable at portfolio level.
- **Likely question:** *"Then why include it?"* → Because the honest finding is
  that company revenue is forecastable and individual revenue is not.

### 10. Sales Forecasting — 1 min 30 s

- **Open:** Streamlit → **Sales Forecast**.
- **Show:** the forecast with its prediction interval.
- **Explain:** different task from prediction — one company series, projected
  from its own history. Six model families compared;
  selection rule fixed in advance.
- **Results to mention:** Theta: Theta (seasonality auto-tested); test MAPE 7.77% but
  quote the **backtest mean of 14.56%** over 7 folds;
  6 months (2026-01 to 2026-06) totalling ₹1.58 Cr, 80%
  interval ₹1.00 Cr to ₹2.16 Cr, against ₹1.50 Cr in the
  previous six months.
- **Likely question:** *"Why is the interval so wide?"* → Short history and a
  univariate model; a narrow interval here would be a false claim.

### 11. SQL Analytics — 1 min

- **Open:** a terminal — `sqlite3 data/customer_revenue_intelligence.db` — and
  paste the reconciliation query from `outputs/viva/sql_demo_script.md`.
- **Show:** the query returning revenue, profit, margin, orders, customers.
- **Explain:** this layer is an **independent implementation**; agreement with
  Python is evidence, not a copy.
- **Results to mention:** 11 tables, 2 views,
  57 queries; all 56 validation and
  20 quality checks pass; the query returns exactly
  ₹6.01 Cr and 23.35%.
- **Likely question:** *"Which advanced SQL did you use?"* → Window functions
  in 35 queries, CTEs in 27, ranking in 22, running totals, LAG/LEAD.

### 12. Power BI — 1 min

- **Open:** `outputs/screenshots/58_powerbi_executive_overview_MOCKUP.png`.
- **Show:** the page design.
- **Explain, in your first sentence:** "Power BI Desktop is Windows-only and
  was not available, so this is a design mockup rendered from the real data,
  not a screenshot." Then say what **is** complete.
- **Results to mention:** 13-table star schema,
  9 relationships, 84 DAX measures in
  10 folders, 48/48 validated
  against SQL, 32 consistency checks passing.
- **Likely question:** *"Why not just install it?"* → It does not run on
  Linux; the build guide and every artefact needed are in `powerbi/`.

### 13. Streamlit Application — 2 min

- **Open:** the running app; walk Home → Executive Overview → Customer
  Segmentation → Sales Forecast → Data Explorer, and download one CSV.
- **Show:** the filters changing every chart on a page; the CSV download.
- **Explain:** it loads the persisted `.pkl` models and computes no metric of
  its own, so a number on screen cannot drift from the report.
- **Results to mention:** 12 pages,
  40/40 headless tests pass.
- **Likely question:** *"Is it deployed?"* → No; it runs locally. Deployment is
  future scope.

### 14. Business Recommendations — 1 min

- **Open:** Streamlit → **Business Recommendations**.
- **Show:** two or three cards with their evidence.
- **Explain:** 18 recommendations, each generated from the
  pipeline's own outputs with its supporting metric and source.
- **Results to mention:** protect the top decile (45.39% of revenue);
  work the 52-customer inactive list; manage category mix; test
  the discount relationship rather than acting on it.
- **Likely question:** *"Will these increase revenue?"* → The project cannot
  prove that; they are evidence-linked, not causally proven.

### 15. Conclusion — 45 s

- **Open:** PPT slide 20.
- **Explain:** raw transactions in, business decisions out; every number
  traceable; every model chosen by a rule fixed in advance; weak results
  reported as weak.
- **Result to mention:** 135 automated checks,
  134 pass, 0 fail.
- **Close with:** "I'm happy to take questions, and the application is running
  if you'd like to see anything again."

---

## Compressed 10-minute running order

1 Introduction (30 s) → 2 Problem (45 s) → 3 Dataset (45 s) → 4 Cleaning
(45 s) → 5 EDA (1 min 30 s) → 7 K-Means, mentioning RFM inside it (1 min 30 s)
→ 8 CLV (1 min) → 9 Prediction (1 min) → 10 Forecasting (1 min) → 13 Streamlit
(1 min) → 15 Conclusion (30 s).

## The four things to say even if you run out of time

1. The data is synthetic.
2. The top 20% of customers produce 64.33% of revenue, and two
   independent methods identify the same group.
3. Company forecasting works (14.56% backtest MAPE); individual
   prediction does not (R² 0.0557) — and the project says both.
4. The Power BI pages are design mockups, not screenshots.
