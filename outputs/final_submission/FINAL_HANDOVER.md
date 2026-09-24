# FINAL HANDOVER

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

**Read this document before you submit. Everything else is detail.**

---

## PROJECT

**Customer Revenue Intelligence: An Interactive Data Science Platform for
Customer Segmentation, Revenue Prediction and Business Growth**

MBA (Data Science & AI) Summer Internship Project · Apex Institute of
Management, Chandigarh University · internship at Tutorsuite Technologies LLP,
Kolkata, 1st June to 12th July, under the guidance of Kuldeep Dubey.

## PURPOSE

Retail businesses record transactions far faster than they convert them into
decisions. This platform closes that gap: it takes a transaction dataset from a
raw file through cleaning, exploratory analysis, two independent customer
segmentations, customer value analysis, next-quarter revenue prediction and
company-level forecasting, reconciles every metric against an independent SQL
implementation, and delivers the results through a Power BI semantic model and
a working application — such that every reported number is traceable to the
file that produced it.

## TECHNOLOGIES

Python 3.11 · pandas · NumPy · SciPy · scikit-learn 1.8.0 · statsmodels 0.15.0
· joblib · Matplotlib · Seaborn · Plotly · SQLite · Power BI (DAX, Power Query
M) · Streamlit · Jupyter · python-docx · python-pptx

## MAIN ANALYTICS

| Stage | Output |
|---|---|
| Cleaning | 18,819 raw → 18,670 validated lines; every business rule returns zero failures; 28 engineered columns |
| EDA | ₹6.01 Cr delivered revenue at 23.35% margin, 12,212 orders, AOV ₹4,917.83 |
| RFM | 1,984 customers into 11 segments at reference date 2026-01-01 |
| SQL | 11 tables, 2 views, 57 queries; 56/56 checks pass |

## MACHINE LEARNING

| Model | Specification | Result |
|---|---|---|
| K-Means | K = 4, log1p → StandardScaler | Silhouette 0.3534; ARI vs RFM 0.3952 |
| Customer value | Random forest, out-of-time | MAE ₹2,793, R² 0.2705, Spearman 0.4869 |
| Revenue prediction | Linear regression, 24 features, 10,393-row panel | Test R² 0.0557, MAE ₹5,658 — **weak, reported as weak** |
| Forecasting | Theta: Theta (seasonality auto-tested), 6 months | Backtest mean MAPE 14.56% |

Every model was selected by a rule fixed **before** the results were seen.

## DASHBOARDS

| Surface | State |
|---|---|
| Streamlit application | **Working.** 12 pages, 40/40 headless tests pass, 12 real screenshots |
| Power BI semantic model | **Complete and validated.** 13 tables, 9 relationships, 84 DAX measures, 48/48 matching SQL |
| Power BI report pages | **Not built.** Desktop is Windows-only; nine design mockups exist and are labelled as mockups everywhere |

## REPORT

`FINAL_SUBMISSION/01_REPORT/Final_Internship_Report.pdf` (and `.docx`)
40 pages · A4 · Times New Roman · 9 figures · 16 tables · 38 references

## PPT

`FINAL_SUBMISSION/02_PRESENTATION/Final_Internship_Presentation.pptx`
(and `.pdf`) — 22 slides on the university template, speaker notes on every
slide

## APPLICATION

```bash
streamlit run app.py        # then open http://localhost:8501
```

## DATABASE / SQL

`sql/schema.sql` · `sql/analysis_queries.sql` · `sql/business_queries.sql` ·
`sql/powerbi_views.sql` · `sql/load_database.py`
Database: `data/customer_revenue_intelligence.db`

The reconciliation anchor — this query must return ₹6.01 Cr and
23.35% in Python, SQL and DAX alike:

```sql
SELECT ROUND(SUM(oi.sales), 2) AS revenue,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

## DATA

**Synthetic**, generated with seed 42. Not real company data.

18,819 raw → 18,670 clean order lines · 1,984
purchasing customers of 2,000 registered · 61 products
in 6 categories · 35 cities, 21 states,
5 regions · 01 January 2023 to 31 December 2025 (36 months) ·
13,251 orders across all statuses.

Revenue counts **delivered lines only**; ₹62.55 L (9.43%)
of booked value is lost to returns and cancellations and is analysed
separately.

## KEY FINDINGS

1. Value is concentrated — top 10% of customers = 45.39% of revenue, top
   20% = 64.33%.
2. Champions are 16.84% of customers but 53.83% of revenue.
3. Two independent methods — RFM rules and K-Means — identify substantially the
   same high-value group (ARI 0.3952).
4. 52 high-value customers are inactive for 180+ days, holding
   ₹26.51 L of historical revenue.
5. Repeat customers are 89.42% of the base and 98.59% of
   revenue.
6. Volume leader ≠ margin leader — Electronics is 50.10% of
   revenue at 10.85% margin; Beauty earns
   46.49%.
7. Zero-discount orders carry the best margin in 6 of
   6 categories — an association, not a proven cause.
8. Reliability differs by horizon — company forecasting works
   (14.56% backtest MAPE); individual prediction does not
   (R² 0.0557).

## KEY LIMITATIONS

1. Synthetic dataset — methods transfer, numbers describe no real business.
2. 36-month history — thin for seasonal estimation.
3. Weak individual prediction — portfolio level only.
4. Univariate forecast — no price, promotion or holiday input.
5. Association, not causation.
6. No churn label — the project reports inactivity and never churn.
7. Power BI `.pbix` not built — Windows-only tool unavailable.
8. No user testing.
9. No deployment, scheduling or drift monitoring.

## FUTURE SCOPE

Validate on real data under a data-protection agreement · define an operational
inactivity label with the business · reframe prediction as a two-stage problem
· add external regressors to the forecast · run a controlled discount
experiment · operationalise with scheduled runs and drift monitoring · complete
the Power BI build on Windows.

## FINAL MANUAL ACTIONS

| # | Action |
|---|---|
| 1 | Fill `[UID]` — report title page and acknowledgement |
| 2 | Fill `[TO BE FILLED]` UID — PPT slide 1 |
| 3 | Sign the bonafide certificate page |
| 4 | Add a Declaration if your department requires one (wording provided) |
| 5 | Add the internship year if your department wants it printed |
| 6 | Read the PPT once for spelling |
| 7 | Create the ZIP and back it up to USB, cloud and GitHub |
| 8 | Open the application once and click every page before the viva |
| 9 | Submit per your department's instructions |

## THE THREE SENTENCES TO HAVE WORD-PERFECT

1. "The dataset is synthetic, generated with a fixed seed for academic
   demonstration — it describes no real company."
2. "Power BI Desktop is Windows-only and wasn't available, so those pages are
   design mockups rendered from the real data, not screenshots."
3. "Customer-level prediction is weak at R² 0.0557, and I report it as
   weak — 53.0% of customer-quarters have no order at all."

## PROJECT STATUS

135 automated checks · **134 pass ·
0 fail**. Sixteen components: 15 complete, 1 partial (the
Power BI `.pbix`, for the documented Windows-only reason), 0 missing.
