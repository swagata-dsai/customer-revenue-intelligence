# Cross-Document Consistency

*Generated 2026-09-24 by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*

## How consistency is enforced, not merely checked

The report, the presentation, the viva pack and this audit are all **generated
by scripts that read the same file**: `outputs/tables/report_facts.json`,
written by `scripts/report_facts.py` from the pipeline's own outputs.

| Document | Generator | Source of every number |
|---|---|---|
| Report (`.docx`/`.pdf`) | `scripts/build_report.py` | `report_facts.json` |
| Presentation (`.pptx`/`.pdf`) | `scripts/build_presentation.py` | `report_facts.json` |
| Viva pack (18 files) | `scripts/build_viva.py` | `report_facts.json` |
| README and this audit | `scripts/build_packaging.py` | `report_facts.json` |

No number is typed by hand into any of them. A figure therefore cannot differ
between documents unless one of them is stale, which is why every document is
rebuilt whenever the fact pack changes.

## Verified values

| Item | Report | PPT | README / Viva | Code / Actual | Status |
|------|--------|-----|---------------|---------------|--------|
| Project title | Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth | Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth | Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth | Customer Revenue Intelligence: An Interactive Data Science Platform for Customer Segmentation, Revenue Prediction and Business Growth | MATCH |
| Raw order lines | 18,819 | 18,819 | 18,819 | 18,819 | MATCH |
| Cleaned order lines | 18,670 | 18,670 | 18,670 | 18,670 | MATCH |
| Purchasing customers | 1,984 | 1,984 | 1,984 | 1,984 | MATCH |
| Products / categories | 61 products, 6 categories | 61 products, 6 categories | 61 products, 6 categories | 61 products, 6 categories | MATCH |
| Regions | 5 | 5 | 5 | 5 | MATCH |
| Date range | 01 January 2023 – 31 December 2025 | 01 January 2023 – 31 December 2025 | 01 January 2023 – 31 December 2025 | 01 January 2023 – 31 December 2025 | MATCH |
| Observation months | 36 months | 36 months | 36 months | 36 months | MATCH |
| Delivered revenue | ₹6.01 Cr | ₹6.01 Cr | ₹6.01 Cr | ₹6.01 Cr | MATCH |
| Profit margin | 23.35% | 23.35% | 23.35% | 23.35% | MATCH |
| Delivered orders | 12,212 | 12,212 | 12,212 | 12,212 | MATCH |
| Average order value | ₹4,917.83 | ₹4,917.83 | ₹4,917.83 | ₹4,917.83 | MATCH |
| Top-20% revenue share | 64.33% | 64.33% | 64.33% | 64.33% | MATCH |
| RFM reference date | 2026-01-01 | 2026-01-01 | 2026-01-01 | 2026-01-01 | MATCH |
| RFM segments | 11 | 11 | 11 | 11 | MATCH |
| Champions revenue share | 53.83% | 53.83% | 53.83% | 53.83% | MATCH |
| Number of clusters (K) | K = 4 | K = 4 | K = 4 | K = 4 | MATCH |
| Silhouette | 0.3534 | 0.3534 | 0.3534 | 0.3534 | MATCH |
| ARI: RFM vs clusters | 0.3952 | 0.3952 | 0.3952 | 0.3952 | MATCH |
| Customer-value model | Random forest | Random forest | Random forest | Random forest | MATCH |
| Customer-value R² | 0.2705 | 0.2705 | 0.2705 | 0.2705 | MATCH |
| Prediction model | Linear regression | Linear regression | Linear regression | Linear regression | MATCH |
| Prediction test R² | 0.0557 | 0.0557 | 0.0557 | 0.0557 | MATCH |
| Prediction test MAE | ₹5,658 | ₹5,658 | ₹5,658 | ₹5,658 | MATCH |
| Forecast model | Theta: Theta (seasonality auto-tested) | Theta: Theta (seasonality auto-tested) | Theta: Theta (seasonality auto-tested) | Theta: Theta (seasonality auto-tested) | MATCH |
| Forecast horizon | 6 months | 6 months | 6 months | 6 months | MATCH |
| Forecast backtest MAPE | 14.56% | 14.56% | 14.56% | 14.56% | MATCH |
| SQL queries | 57 | 57 | 57 | 57 | MATCH |
| DAX measures | 84 | 84 | 84 | 84 | MATCH |
| Streamlit pages | 12 | 12 | 12 | 12 | MATCH |
| Streamlit tests | 40/40 pass | 40/40 pass | 40/40 pass | 40/40 pass | MATCH |
| Project audit checks | 135 (134 pass, 0 fail) | 135 (134 pass, 0 fail) | 135 (134 pass, 0 fail) | 135 (134 pass, 0 fail) | MATCH |

## Inconsistencies found and corrected

These were real defects, found by this audit and by the automated project
audit, and fixed at source before the documents were regenerated.

| # | Inconsistency | Found in | Resolution |
|---|---|---|---|
| 1 | Four of nine pipeline commands named modules/functions that do not exist (`run_cleaning`, `src.customer_value`, `src.revenue_prediction`, `src.sql_analysis`) | Report, User Manual | Corrected to `run_pipeline`, `src.clv.run_clv`, `src.prediction.run_prediction`, `src.sql_analytics.run_sql_workflow`; all nine import-tested, report rebuilt |
| 2 | CLV baseline described as a "naive group-average baseline" when the actual baseline is "last-12-month profit repeats" (the group average is the scoring fallback for customers with no recent order) | Report Section 3.6, viva master summary | Wording corrected in both generators; both rebuilt |
| 3 | Implementation flowchart showed "140/141 checks pass" from an earlier audit run | Report Chapter 3, PPT slide 8 | Diagrams regenerated from the current fact pack; both documents rebuilt |
| 4 | Appendix quoted `models/kmeans_customer_segments.pkl`; the persisted artefact is `kmeans_customer_segmentation.pkl` | Report Appendix A.1 | Filename corrected; audit's broken-reference check now passes |
| 5 | Documentation described recency as "the earliest warning sign of churn" in a project that defines no churn event | `src/rfm.py`, `rfm_methodology.md` | Reworded at source, report regenerated, notebook 03 re-executed |
| 6 | Table of Contents resolved REFERENCES and APPENDIX to page 6 (a body page that merely contains the word) | Report front matter | Page resolution made line-exact for short headings; all 180 anchors now resolve |

## Claims checked against implementation

| Claim made in the documents | Supported by | Verdict |
|---|---|---|
| "12-page Streamlit application" | 12 modules in `pages/`, 40/40 headless tests | Supported |
| "84 DAX measures validated against SQL" | `powerbi/validation/`, 48/48 match | Supported |
| "57 SQL queries" | `sql/analysis_queries.sql` + `sql/business_queries.sql` | Supported |
| "Power BI dashboard" | Model, measures, M scripts, theme, build guide — **but no .pbix** | Qualified everywhere as design mockups; no screenshot claimed |
| "Leakage audit found none" | `scripts/audit_project.py` Part D recomputes sampled feature rows independently | Supported |
| "Reproducible from seed 42" | Audit reproduces K-Means labels from the persisted scaler and model exactly | Supported |
| "Predictive CLV" | Reported as **estimated forward value**, never as a guarantee; historical value reported separately | Correctly distinguished |
| "Churn" | Never used to describe a result; the audit scans every document for it | Correctly absent |

## Residual, deliberate differences

Not every difference is an error. These are intentional:

| Difference | Reason |
|---|---|
| The report writes `₹`; the PPT writes `Rs` | The university PPT template uses a custom font with no rupee glyph; `Rs` renders reliably everywhere |
| The report has 9 figures, the PPT has 9, the project has 144 | The report and deck use a curated subset; the rest support the pipeline stages |
| The report quotes the forecast backtest MAPE (14.56%), not the test-split MAPE (7.77%) | Deliberate: the backtest mean over folds is the honest expectation, and every document quotes the same one |
