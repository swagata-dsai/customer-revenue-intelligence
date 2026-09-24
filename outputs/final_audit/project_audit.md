# Final Project Audit

*Generated 2026-09-24 by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*

## Component status

| Component | Status | File/Location | Notes |
|-----------|--------|---------------|-------|
| 1. Data generation | COMPLETE | `scripts/generate_dataset.py` → `data/raw/` | 18,819 raw order lines, 23 columns, seed 42; injection log at `data/raw/data_quality_injection_log.json` |
| 2. Data cleaning | COMPLETE | `src/data_cleaning.py` → `data/processed/customer_sales_cleaned.csv` | 18,670 validated lines, 51 columns; 149 duplicates removed; all business rules return zero |
| 3. Data validation | COMPLETE | `scripts/validate_dataset.py`, `scripts/audit_cleaning.py` | Raw extract checked against the generator's ground truth and injection log; cleaning re-audited rule by rule |
| 4. EDA | COMPLETE | `src/eda.py` → `outputs/figures/`, `outputs/reports/eda_summary.md` | ₹6.01 Cr revenue at 23.35% margin; top 20% of customers = 64.33% of revenue |
| 5. RFM analysis | COMPLETE | `src/rfm.py` → `data/processed/customer_rfm_segments.csv` | 1,984 customers into 11 segments at reference date 2026-01-01 |
| 6. K-Means segmentation | COMPLETE | `src/segmentation.py` → `models/kmeans_customer_segmentation.pkl` | K = 4, silhouette 0.3534, ARI vs RFM 0.3952; scaler persisted as `models/rfm_scaler.pkl` |
| 7. CLV analysis | COMPLETE | `src/clv.py` → `models/clv_model.pkl`, `data/processed/customer_clv.csv` | Historical ₹1.40 Cr measured; forward value by random forest, R² 0.2705, Spearman 0.4869 |
| 8. Revenue prediction | COMPLETE | `src/prediction.py` → `models/revenue_prediction_model.pkl` | Linear regression, test R² 0.0557, MAE ₹5,658; reported as weak — 53.0% of customer-quarters are zero |
| 9. Sales forecasting | COMPLETE | `src/forecasting.py` → `models/forecasting_model.pkl` | Theta: Theta (seasonality auto-tested), 6-month horizon, backtest mean MAPE 14.56% |
| 10. SQL analytics | COMPLETE | `sql/`, `src/sql_analytics.py` → `data/customer_revenue_intelligence.db` | 11 tables, 2 views, 57 queries; 56/56 validation checks pass |
| 11. Power BI dashboard | PARTIALLY COMPLETE | `powerbi/`, `src/powerbi_prep.py`, `src/powerbi_dax.py` | Semantic model, 84 DAX measures (48/48 validated against SQL), Power Query M, theme and build guide are complete. **The .pbix is not built**: Power BI Desktop is Windows-only and was unavailable. The nine page layouts in `outputs/figures/powerbi/mockups/` are design mockups rendered from the real data and are labelled as such everywhere. |
| 12. Streamlit application | COMPLETE | `app.py`, `pages/` (12 modules), `src/dashboard_utils.py`, `src/data_loader.py` | 12 pages; headless tests 40/40 pass (`tests/test_streamlit_app.py`); 12 real screenshots in `outputs/figures/streamlit/` |
| 13. Business recommendations | COMPLETE | `pages/recommendations.py`, `powerbi/` recommendation table | 18 recommendations, each carrying its evidence, supporting metric and analytical source |
| 14. Internship report | COMPLETE | `outputs/reports/…_Report.docx` and `.pdf` | 40 pages, A4, Times New Roman, university format; built by `scripts/build_report.py`; checklist at `outputs/reports/report_validation_checklist.md` |
| 15. PPT | COMPLETE | `outputs/presentation/…_Presentation.pptx` and `.pdf` | 22 slides built on the university-supplied template (`assets/templates/`), speaker notes on every slide; built by `scripts/build_presentation.py` |
| 16. Viva preparation | COMPLETE | `outputs/viva/` (18 files) | 319 questions and answers plus master summary, speaking script, top-20 and revision sheet; built by `scripts/build_viva.py` |

**15 COMPLETE · 1 PARTIALLY COMPLETE · 0 MISSING**

The single PARTIALLY COMPLETE item is Power BI, and the reason is
environmental rather than analytical: Power BI Desktop runs only on Windows
and the project was built on Linux. Everything that can be produced without
Desktop was produced and validated; the .pbix file itself cannot be, and no
screenshot of it is claimed anywhere in the report, the deck or this audit.

## Supporting artefacts on disk

| Artefact | Count / size | Location |
|---|---|---|
| Python modules | 41 files, 30,690 lines | `src/`, `scripts/`, `pages/`, `app.py`, `config.py` |
| Jupyter notebooks | 9 executed | `notebooks/` |
| SQL files | 4 | `sql/` |
| Trained model artefacts | 8 `.pkl` + 4 metadata | `models/` |
| Figures | 144 | `outputs/figures/` |
| Output tables | 238 | `outputs/tables/` |
| Written reports | 13 | `outputs/reports/` |
| Viva documents | 32 | `outputs/viva/` |
| Test suite | 1 module | `tests/` |

## Automated verification

`python scripts/audit_project.py` runs **135 checks** across
structure, pipeline dependencies, cross-dataset consistency, model
reproducibility, leakage and integration: **134 pass,
0 fail**.

## Defects found and fixed during this packaging step

| Defect | Where | Fix |
|---|---|---|
| Four of the nine pipeline commands in the report's User Manual named modules or functions that do not exist (`run_cleaning`, `src.customer_value`, `src.revenue_prediction`, `src.sql_analysis`) | `scripts/build_report.py` User Manual | Corrected to the real entry points (`run_pipeline`, `src.clv.run_clv`, `src.prediction.run_prediction`, `src.sql_analytics.run_sql_workflow`); each was import-tested before the report was rebuilt |
| `requirements.txt` omitted four packages the build scripts import (`python-docx`, `python-pptx`, `pypdf`, `Pillow`) | `requirements.txt` | Added in a clearly separated optional section |
| No `LICENSE` file | repository root | MIT licence added |
| README was an 835-line step-by-step build log rather than a repository README | `README.md` | Rewritten to the standard structure; the build log preserved at `docs/project_build_log.md` |

## Items deliberately NOT marked complete

- **Power BI .pbix** — cannot be produced without Windows; documented above.
- **Production deployment, scheduled runs, drift monitoring** — never
  implemented, listed as future scope in the report and this audit.
- **User testing of the dashboard and application** — not performed.
