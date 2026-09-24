# Final Project Inventory

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

**139 inventory entries, every one verified present on disk.** Nothing
is listed that does not exist.

| Category | Entries |
|---|---|
| A. Data | 11 |
| B. Python code | 40 |
| C. Notebooks | 9 |
| D. SQL | 5 |
| E. Models | 12 |
| F. Power BI | 4 |
| G. Streamlit | 2 |
| H. Report | 3 |
| I. Presentation | 2 |
| J. Viva | 32 |
| K. Documentation | 13 |
| L. Screenshots | 2 |
| M. Configuration | 4 |

| Category | File | Purpose | Status |
|----------|------|---------|--------|
| A. Data | `data/raw/customer_sales_raw.csv` | Generated extract — 18,819 lines, 23 columns, seed 42 | PRESENT · 3.8 MB |
| A. Data | `data/raw/data_quality_injection_log.json` | Ground truth: every defect the generator injected | PRESENT · 4 KB |
| A. Data | `data/processed/customer_sales_cleaned.csv` | Cleaned dataset — 18,670 lines, 51 columns | PRESENT · 6.6 MB |
| A. Data | `data/processed/customer_rfm_segments.csv` | RFM scores and 11 segment assignments | PRESENT · 341 KB |
| A. Data | `data/processed/customer_ml_segments.csv` | K-Means cluster assignments (K = 4) | PRESENT · 527 KB |
| A. Data | `data/processed/customer_clv.csv` | Historical and estimated forward customer value | PRESENT · 336 KB |
| A. Data | `data/processed/revenue_modeling_dataset.csv` | Customer-quarter panel — 10,393 rows | PRESENT · 2.5 MB |
| A. Data | `data/processed/clv_modeling_dataset.csv` | Customer-value modelling panel | PRESENT · 665 KB |
| A. Data | `data/processed/monthly_sales_timeseries.csv` | Monthly revenue series — 36 months | PRESENT · 3 KB |
| A. Data | `data/processed/revenue_forecast.csv` | 6-month forecast with prediction intervals | PRESENT · 4 KB |
| A. Data | `data/customer_revenue_intelligence.db` | SQLite database — 11 tables, 2 views | PRESENT · 5.5 MB |
| B. Python code | `app.py` | Streamlit entry point — 12 pages | PRESENT · 4 KB |
| B. Python code | `config.py` | Central paths and project constants | PRESENT · 3 KB |
| B. Python code | `src/data_cleaning.py` | Rule-driven cleaning (`run_pipeline`) | PRESENT · 55 KB |
| B. Python code | `src/eda.py` | Exploratory analysis (`run_eda`) | PRESENT · 113 KB |
| B. Python code | `src/rfm.py` | RFM scoring and segment rules (`run_rfm`) | PRESENT · 66 KB |
| B. Python code | `src/segmentation.py` | K-Means and K selection (`run_segmentation`) | PRESENT · 72 KB |
| B. Python code | `src/clv.py` | Customer value (`run_clv`) | PRESENT · 120 KB |
| B. Python code | `src/prediction.py` | Revenue prediction (`run_prediction`) | PRESENT · 101 KB |
| B. Python code | `src/forecasting.py` | Time-series forecasting (`run_forecasting`) | PRESENT · 78 KB |
| B. Python code | `src/sql_analytics.py` | Database build and queries (`run_sql_workflow`) | PRESENT · 41 KB |
| B. Python code | `src/database.py` | SQLite connection and schema helpers | PRESENT · 16 KB |
| B. Python code | `src/powerbi_prep.py` | Power BI extracts and theme (`run_powerbi_prep`) | PRESENT · 175 KB |
| B. Python code | `src/powerbi_dax.py` | DAX library — 84 measures | PRESENT · 25 KB |
| B. Python code | `src/data_loader.py` | Database-first loaders with CSV fallback | PRESENT · 16 KB |
| B. Python code | `src/dashboard_utils.py` | Shared theme, KPI cards, chart helper | PRESENT · 15 KB |
| B. Python code | `scripts/generate_dataset.py` | Synthetic data generator | PRESENT · 40 KB |
| B. Python code | `scripts/validate_dataset.py` | Raw data validation against ground truth | PRESENT · 12 KB |
| B. Python code | `scripts/audit_cleaning.py` | Cleaning re-audit | PRESENT · 3 KB |
| B. Python code | `scripts/audit_project.py` | 135-check project audit | PRESENT · 62 KB |
| B. Python code | `scripts/report_facts.py` | Builds the single fact pack | PRESENT · 21 KB |
| B. Python code | `scripts/report_diagrams.py` | Report and deck diagrams | PRESENT · 17 KB |
| B. Python code | `scripts/build_report.py` | Generates the report | PRESENT · 104 KB |
| B. Python code | `scripts/build_presentation.py` | Generates the deck | PRESENT · 51 KB |
| B. Python code | `scripts/build_viva.py` | Generates the viva pack | PRESENT · 177 KB |
| B. Python code | `scripts/build_packaging.py` | Generates README and packaging audit | PRESENT · 86 KB |
| B. Python code | `scripts/build_demo.py` | Generates the demo pack and screenshots | PRESENT · 140 KB |
| B. Python code | `scripts/build_submission.py` | Generates this submission package | PRESENT · 103 KB |
| B. Python code | `tests/test_streamlit_app.py` | 40 headless application tests | PRESENT · 18 KB |
| B. Python code | `pages/about.py` | Streamlit page: About | PRESENT · 10 KB |
| B. Python code | `pages/customers.py` | Streamlit page: Customers | PRESENT · 16 KB |
| B. Python code | `pages/data_explorer.py` | Streamlit page: Data Explorer | PRESENT · 13 KB |
| B. Python code | `pages/executive.py` | Streamlit page: Executive | PRESENT · 9 KB |
| B. Python code | `pages/forecasting.py` | Streamlit page: Forecasting | PRESENT · 12 KB |
| B. Python code | `pages/home.py` | Streamlit page: Home | PRESENT · 7 KB |
| B. Python code | `pages/prediction.py` | Streamlit page: Prediction | PRESENT · 19 KB |
| B. Python code | `pages/products.py` | Streamlit page: Products | PRESENT · 14 KB |
| B. Python code | `pages/recommendations.py` | Streamlit page: Recommendations | PRESENT · 5 KB |
| B. Python code | `pages/regional.py` | Streamlit page: Regional | PRESENT · 9 KB |
| B. Python code | `pages/revenue.py` | Streamlit page: Revenue | PRESENT · 13 KB |
| B. Python code | `pages/segmentation.py` | Streamlit page: Segmentation | PRESENT · 17 KB |
| C. Notebooks | `notebooks/01_data_cleaning.ipynb` | Executed notebook: data cleaning | PRESENT · 627 KB |
| C. Notebooks | `notebooks/02_exploratory_data_analysis.ipynb` | Executed notebook: exploratory data analysis | PRESENT · 7.8 MB |
| C. Notebooks | `notebooks/03_rfm_customer_analysis.ipynb` | Executed notebook: rfm customer analysis | PRESENT · 3.7 MB |
| C. Notebooks | `notebooks/04_kmeans_customer_segmentation.ipynb` | Executed notebook: kmeans customer segmentation | PRESENT · 3.9 MB |
| C. Notebooks | `notebooks/05_customer_lifetime_value.ipynb` | Executed notebook: customer lifetime value | PRESENT · 2.7 MB |
| C. Notebooks | `notebooks/06_revenue_prediction.ipynb` | Executed notebook: revenue prediction | PRESENT · 2.1 MB |
| C. Notebooks | `notebooks/07_sales_forecasting.ipynb` | Executed notebook: sales forecasting | PRESENT · 2.2 MB |
| C. Notebooks | `notebooks/08_sql_business_analysis.ipynb` | Executed notebook: sql business analysis | PRESENT · 2.4 MB |
| C. Notebooks | `notebooks/09_powerbi_data_model.ipynb` | Executed notebook: powerbi data model | PRESENT · 4.4 MB |
| D. SQL | `sql/schema.sql` | Normalised schema — 11 tables | PRESENT · 15 KB |
| D. SQL | `sql/analysis_queries.sql` | Analysis queries | PRESENT · 32 KB |
| D. SQL | `sql/business_queries.sql` | Business queries | PRESENT · 25 KB |
| D. SQL | `sql/powerbi_views.sql` | Views feeding the Power BI model | PRESENT · 18 KB |
| D. SQL | `sql/load_database.py` | Database loader | PRESENT · 2 KB |
| E. Models | `models/kmeans_customer_segmentation.pkl` | K-Means, K = 4 | PRESENT · 9 KB |
| E. Models | `models/rfm_scaler.pkl` | log1p → StandardScaler pipeline | PRESENT · 1 KB |
| E. Models | `models/pca_rfm.pkl` | 2-component PCA (visualisation only) | PRESENT · 1 KB |
| E. Models | `models/clv_model.pkl` | Random forest — forward customer value | PRESENT · 5.3 MB |
| E. Models | `models/clv_preprocessor.pkl` | Customer-value preprocessing | PRESENT · 3 KB |
| E. Models | `models/revenue_prediction_model.pkl` | Linear regression — next-quarter revenue | PRESENT · 8 KB |
| E. Models | `models/revenue_prediction_preprocessor.pkl` | Prediction preprocessing | PRESENT · 7 KB |
| E. Models | `models/forecasting_model.pkl` | Theta: Theta (seasonality auto-tested) — monthly forecast | PRESENT · 3 KB |
| E. Models | `models/segmentation_model_metadata.json` | K selection rules and diagnostics | PRESENT · 1 KB |
| E. Models | `models/clv_model_metadata.json` | Value model selection rule and metrics | PRESENT · 2 KB |
| E. Models | `models/revenue_model_metadata.json` | Prediction selection rule and metrics | PRESENT · 2 KB |
| E. Models | `models/forecasting_metadata.json` | Forecast selection rule and metrics | PRESENT · 1 KB |
| F. Power BI | `powerbi/POWERBI_BUILD_GUIDE.md` | Step-by-step build instructions | PRESENT · 9 KB |
| F. Power BI | `powerbi/relationships.csv` | 9 model relationships | PRESENT · 1 KB |
| F. Power BI | `powerbi/table_catalog.csv` | 13 model tables | PRESENT · 2 KB |
| F. Power BI | `powerbi/validation_checklist.csv` | Pre-build checklist | PRESENT · 4 KB |
| G. Streamlit | `outputs/reports/streamlit_testing_report.md` | 40/40 headless test results | PRESENT · 16 KB |
| G. Streamlit | `.streamlit/config.toml` | Theme configuration | PRESENT · 0 KB |
| H. Report | `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx` | 40-page report (Word) | PRESENT · 2.6 MB |
| H. Report | `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.pdf` | 40-page report (PDF) | PRESENT · 2.0 MB |
| H. Report | `outputs/reports/report_validation_checklist.md` | 32-item report validation | PRESENT · 10 KB |
| I. Presentation | `outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx` | 22 slides (PowerPoint) | PRESENT · 3.0 MB |
| I. Presentation | `outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pdf` | 22 slides (PDF) | PRESENT · 2.2 MB |
| J. Viva | `outputs/viva/01_basic_viva_questions.md` | 01 basic viva questions | PRESENT · 9 KB |
| J. Viva | `outputs/viva/02_intermediate_technical_questions.md` | 02 intermediate technical questions | PRESENT · 13 KB |
| J. Viva | `outputs/viva/03_advanced_data_science_questions.md` | 03 advanced data science questions | PRESENT · 11 KB |
| J. Viva | `outputs/viva/04_sql_viva.md` | 04 sql viva | PRESENT · 8 KB |
| J. Viva | `outputs/viva/05_powerbi_viva.md` | 05 powerbi viva | PRESENT · 7 KB |
| J. Viva | `outputs/viva/06_streamlit_viva.md` | 06 streamlit viva | PRESENT · 7 KB |
| J. Viva | `outputs/viva/07_business_questions.md` | 07 business questions | PRESENT · 7 KB |
| J. Viva | `outputs/viva/08_challenging_questions.md` | 08 challenging questions | PRESENT · 11 KB |
| J. Viva | `outputs/viva/09_trick_questions.md` | 09 trick questions | PRESENT · 7 KB |
| J. Viva | `outputs/viva/10_mock_viva_easy.md` | 10 mock viva easy | PRESENT · 3 KB |
| J. Viva | `outputs/viva/11_mock_viva_medium.md` | 11 mock viva medium | PRESENT · 5 KB |
| J. Viva | `outputs/viva/12_mock_viva_difficult.md` | 12 mock viva difficult | PRESENT · 7 KB |
| J. Viva | `outputs/viva/business_viva.md` | Business viva | PRESENT · 5 KB |
| J. Viva | `outputs/viva/difficult_professor_questions.md` | Difficult professor questions | PRESENT · 9 KB |
| J. Viva | `outputs/viva/final_demo_order.md` | Final demo order | PRESENT · 4 KB |
| J. Viva | `outputs/viva/final_revision_sheet.md` | Final revision sheet | PRESENT · 6 KB |
| J. Viva | `outputs/viva/last_minute_revision.md` | Last minute revision | PRESENT · 3 KB |
| J. Viva | `outputs/viva/live_demo_script.md` | Live demo script | PRESENT · 8 KB |
| J. Viva | `outputs/viva/live_failure_handling.md` | Live failure handling | PRESENT · 5 KB |
| J. Viva | `outputs/viva/ml_live_viva.md` | Ml live viva | PRESENT · 7 KB |
| J. Viva | `outputs/viva/one_line_answers.md` | One line answers | PRESENT · 5 KB |
| J. Viva | `outputs/viva/powerbi_demo_script.md` | Powerbi demo script | PRESENT · 11 KB |
| J. Viva | `outputs/viva/presentation_speaking_script.md` | Presentation speaking script | PRESENT · 18 KB |
| J. Viva | `outputs/viva/professor_presentation_questions.md` | Professor presentation questions | PRESENT · 6 KB |
| J. Viva | `outputs/viva/project_master_summary.md` | Project master summary | PRESENT · 18 KB |
| J. Viva | `outputs/viva/rapid_fire_questions.md` | Rapid fire questions | PRESENT · 4 KB |
| J. Viva | `outputs/viva/rapid_fire_viva.md` | Rapid fire viva | PRESENT · 6 KB |
| J. Viva | `outputs/viva/sql_demo_script.md` | Sql demo script | PRESENT · 10 KB |
| J. Viva | `outputs/viva/streamlit_demo_script.md` | Streamlit demo script | PRESENT · 10 KB |
| J. Viva | `outputs/viva/top_20_viva_questions.md` | Top 20 viva questions | PRESENT · 11 KB |
| J. Viva | `outputs/viva/trick_questions.md` | Trick questions | PRESENT · 7 KB |
| J. Viva | `outputs/viva/why_questions.md` | Why questions | PRESENT · 5 KB |
| K. Documentation | `README.md` | Repository README | PRESENT · 23 KB |
| K. Documentation | `docs/reproducibility_guide.md` | Rebuild from scratch | PRESENT · 8 KB |
| K. Documentation | `docs/project_build_log.md` | Original step-by-step build log | PRESENT · 50 KB |
| K. Documentation | `docs/STEP2_Dataset_Design.md` | Dataset design note | PRESENT · 26 KB |
| K. Documentation | `docs/STEP3_Data_Cleaning_Methodology.md` | Cleaning methodology | PRESENT · 14 KB |
| K. Documentation | `outputs/final_audit/cross_document_consistency.md` | Cross document consistency | PRESENT · 8 KB |
| K. Documentation | `outputs/final_audit/final_file_inventory.md` | Final file inventory | PRESENT · 10 KB |
| K. Documentation | `outputs/final_audit/final_submission_checklist.md` | Final submission checklist | PRESENT · 5 KB |
| K. Documentation | `outputs/final_audit/github_readiness_checklist.md` | Github readiness checklist | PRESENT · 4 KB |
| K. Documentation | `outputs/final_audit/live_demo_plan.md` | Live demo plan | PRESENT · 11 KB |
| K. Documentation | `outputs/final_audit/project_audit.md` | Project audit | PRESENT · 6 KB |
| K. Documentation | `outputs/final_audit/project_handover.md` | Project handover | PRESENT · 7 KB |
| K. Documentation | `outputs/final_audit/screenshot_checklist.md` | Screenshot checklist | PRESENT · 15 KB |
| L. Screenshots | `outputs/screenshots/` (81 files) | Numbered demonstration pack: 12 real Streamlit screenshots, 10 labelled Power BI design mockups, 2 dataset previews rendered from the real CSVs, 57 analysis figures | PRESENT · 16.0 MB |
| L. Screenshots | `outputs/figures/` (144 files) | Every figure the pipeline produced | PRESENT · 26.3 MB |
| M. Configuration | `requirements.txt` | Dependencies, derived from an AST scan | PRESENT · 3 KB |
| M. Configuration | `.gitignore` | Version-control exclusions | PRESENT · 2 KB |
| M. Configuration | `LICENSE` | MIT licence | PRESENT · 1 KB |
| M. Configuration | `config.py` | Central paths and constants | PRESENT · 3 KB |

## Not present, and why

| Item | Status | Reason |
|---|---|---|
| `.pbix` Power BI file | NOT PRESENT | Power BI Desktop is a Windows application and was unavailable in the build environment. The semantic model, 84 DAX measures, Power Query scripts, theme and build guide are all present; the nine page layouts are design mockups labelled as such. |
| Deployed application URL | NOT PRESENT | The application runs locally (`streamlit run app.py`). Deployment is listed as future scope, not as an implemented feature. |
| Drift / performance monitoring | NOT PRESENT | Never implemented; named in future scope. |
| Declaration page | NOT PRESENT | The university format supplied for this project does not include one. Add if your department requires it. |
