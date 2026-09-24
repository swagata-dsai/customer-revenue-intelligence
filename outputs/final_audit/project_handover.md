# Project Handover

*Generated 2026-09-24 by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*

## Project Title

**Customer Revenue Intelligence: An Interactive Data Science Platform for
Customer Segmentation, Revenue Prediction and Business Growth**

## Project Type

MBA (Data Science and AI) Summer Internship Project — Apex Institute of
Management, Chandigarh University. Internship carried out at Tutorsuite
Technologies LLP, Kolkata, 1st June to 12th July, under the guidance of
Kuldeep Dubey.

## Main Objective

Build one reproducible platform that takes a transaction dataset through
cleaning, exploratory analysis, dual customer segmentation, customer value
analysis, next-quarter revenue prediction and company-level forecasting;
reconcile the principal metrics against an independent SQL implementation; and
deliver the results through a Power BI semantic model and an interactive
application — such that every reported number is traceable to the file that
produced it.

## Technologies

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Data | pandas, NumPy, SciPy |
| Machine learning | scikit-learn 1.8.0, joblib |
| Time series | statsmodels 0.15.0 |
| Visualisation | Matplotlib, Seaborn, Plotly |
| Database | SQLite (Python's built-in `sqlite3`) |
| Business intelligence | Power BI — DAX, Power Query M |
| Application | Streamlit |
| Notebooks | Jupyter (9 executed) |
| Document generation | python-docx, python-pptx, LibreOffice (PDF), pypdf |

## Main Components

1. Synthetic data generation and raw validation — `scripts/generate_dataset.py`, `scripts/validate_dataset.py`
2. Rule-driven cleaning and feature engineering — `src/data_cleaning.py`
3. Exploratory data analysis — `src/eda.py`
4. RFM scoring and rule-based segments — `src/rfm.py`
5. K-Means segmentation — `src/segmentation.py`
6. Customer value, historical and estimated forward — `src/clv.py`
7. Next-quarter revenue prediction — `src/prediction.py`
8. Monthly revenue forecasting — `src/forecasting.py`
9. SQL database and analytics — `sql/`, `src/sql_analytics.py`
10. Power BI semantic model and DAX library — `src/powerbi_prep.py`, `src/powerbi_dax.py`
11. Streamlit application — `app.py`, `pages/`, `src/dashboard_utils.py`, `src/data_loader.py`
12. Project audit — `scripts/audit_project.py`
13. Report, presentation and viva generators — `scripts/build_report.py`, `build_presentation.py`, `build_viva.py`

## How to Run

```bash
# 1. environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. the application (data and models are already committed)
streamlit run app.py              # opens http://localhost:8501

# 3. verify the whole project
python scripts/audit_project.py   # 135 checks
python -m pytest tests/ -q        # or: python tests/test_streamlit_app.py
```

To rebuild everything from nothing, follow `docs/reproducibility_guide.md`.

## Important Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit entry point — page config, navigation, 12 pages |
| `config.py` | Central paths and project-wide constants |
| `src/data_cleaning.py` | Rule-driven cleaning and feature engineering (`run_pipeline`) |
| `src/eda.py` | Exploratory analysis and figures (`run_eda`) |
| `src/rfm.py` | RFM scoring and segment rules (`run_rfm`) |
| `src/segmentation.py` | K-Means, K selection, diagnostics (`run_segmentation`) |
| `src/clv.py` | Historical value and forward-value model (`run_clv`) |
| `src/prediction.py` | Customer-quarter panel and revenue model (`run_prediction`) |
| `src/forecasting.py` | Time-series models and backtesting (`run_forecasting`) |
| `src/sql_analytics.py` | Database build, validation and query runner (`run_sql_workflow`) |
| `src/powerbi_prep.py` | Power BI extracts, theme, mockups (`run_powerbi_prep`) |
| `src/powerbi_dax.py` | The 84-measure DAX library |
| `src/data_loader.py` | Database-first loaders with CSV fallback, used by the app |
| `src/dashboard_utils.py` | Shared theme, KPI cards, chart helper |
| `sql/schema.sql` | Normalised schema — 11 tables, 2 views |
| `sql/analysis_queries.sql`, `sql/business_queries.sql` | 57 analytical queries |
| `scripts/audit_project.py` | 135-check end-to-end project audit |
| `scripts/report_facts.py` | Builds `outputs/tables/report_facts.json`, the single source of numbers |
| `scripts/build_report.py` | Generates the 40-page report |
| `scripts/build_presentation.py` | Generates the 22-slide deck on the university template |
| `scripts/build_viva.py` | Generates the 18-file viva pack |
| `tests/test_streamlit_app.py` | 40 headless application tests |

## Models

| Artefact | Contents |
|---|---|
| `models/kmeans_customer_segmentation.pkl` | KMeans(n_clusters=4, random_state=42) |
| `models/rfm_scaler.pkl` | Pipeline: log1p → StandardScaler (the clustering preprocessor) |
| `models/pca_rfm.pkl` | 2-component PCA, visualisation only |
| `models/clv_model.pkl` + `clv_preprocessor.pkl` | Random forest for forward customer value |
| `models/revenue_prediction_model.pkl` + `revenue_prediction_preprocessor.pkl` | Linear regression on 24 features |
| `models/forecasting_model.pkl` | Theta: Theta (seasonality auto-tested) fitted on the full monthly series |
| `models/*_metadata.json` | Selection rule, training window, metrics and library versions for each |

## Dashboards

| Surface | State |
|---|---|
| Streamlit application | **Working.** 12 pages, 40/40 tests pass, 12 real screenshots |
| Power BI semantic model | **Complete and validated** — 13 tables, 9 relationships, 84 DAX measures, 48/48 matching SQL |
| Power BI report pages | **Not built.** Desktop is Windows-only; nine design mockups exist and are labelled as mockups |

## Reports

| File | Description |
|---|---|
| `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx` / `.pdf` | 40-page university-format report |
| `outputs/reports/report_validation_checklist.md` | 32-item validation of the report |
| `outputs/presentation/…_Presentation.pptx` / `.pdf` | 22-slide deck with speaker notes |
| `outputs/viva/` | 18-file viva pack, 319 questions |
| `outputs/reports/project_audit.md` | 135-check automated audit |
| `outputs/final_audit/` | This packaging audit (6 documents) |

## Known Limitations

1. **Synthetic dataset** — methods transfer, the numbers describe no real business.
2. **36-month history** — thin for seasonal estimation.
3. **Weak individual prediction** — test R² 0.0557; usable at portfolio level only.
4. **Univariate forecast** — no price, promotion or holiday input.
5. **Association, not causation** — every relationship is observational.
6. **No churn label** — the dataset defines no churn event; inactivity is reported instead.
7. **Power BI .pbix not built** — Windows-only tool unavailable.
8. **No user testing** of the dashboard or application.
9. **No deployment, scheduling or drift monitoring.**

## Future Scope

Validate on real transaction data under a data-protection agreement; define an
operational inactivity label with the business and build a supervised model
against it; reframe next-quarter prediction as a two-stage problem; extend the
forecast with external regressors; run a controlled discount experiment;
operationalise with scheduled re-runs, drift monitoring and performance
tracking; complete the Power BI build on Windows from the supplied artefacts.
