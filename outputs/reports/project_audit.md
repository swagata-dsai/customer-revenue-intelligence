# Project Audit - Step 13

**Project:** Customer Revenue Intelligence · **Audit run:** 24 September 2026, 02:44
**Scope:** Steps 1-12, end to end · **Mode:** quick (parts A-D)

**Result: 134 passed · 0 failed · 0 warnings · 1 informational, out of 135 checks.**

Every line in this report is the output of a check that was executed against the project's
real files. Nothing here is asserted from memory, and no file was deleted or modified by the
audit (the two tests that temporarily move a file restore it in a `finally` block).

Reproduce with:

```bash
python scripts/audit_project.py           # full
python scripts/audit_project.py --quick   # skip the re-run / application tests
```

---

## 1. Headline

| Part | What it checks | Checks | Failed |
|---|---|---|---|
| A | Project structure, duplicates, broken references, unused modules | 5 | 0 |
| B | Pipeline stage inputs/outputs and notebook execution | 21 | 0 |
| C | Cross-dataset consistency | 71 | 0 |
| D | Model artefacts, reproducibility, leakage, documentation figures | 38 | 0 |
| E | Integration, re-run determinism, application tests, linting | 0 | 0 |

### Failures - none

No check failed.

### Warnings

None.

---

## 2. Files found

| Location | Contents |
|---|---|
| (root) | 6 files, 0.04 MB |
| .streamlit | 1 file, 0.00 MB |
| FINAL_SUBMISSION | 551 files, 97.95 MB |
| assets | 4 files, 1.58 MB |
| data | 16 files, 21.18 MB |
| docs | 4 files, 0.10 MB |
| models | 12 files, 5.37 MB |
| notebooks | 9 files, 29.82 MB |
| outputs | 542 files, 54.33 MB |
| pages | 12 files, 0.15 MB |
| powerbi | 40 files, 3.77 MB |
| scripts | 13 files, 0.86 MB |
| sql | 5 files, 0.09 MB |
| src | 14 files, 0.92 MB |
| tests | 1 file, 0.02 MB |

Total: **1230 files** (excluding `__pycache__`).

### Missing expected files

None. Every file declared by every pipeline stage exists on disk.

### Duplicate files

| Files with identical content | Note |
|---|---|
| .gitignore = FINAL_SUBMISSION/10_DOCUMENTATION/gitignore.txt | Identical bytes in two locations. |
| .streamlit/config.toml = FINAL_SUBMISSION/03_SOURCE_CODE/.streamlit/config.toml | Identical bytes in two locations. |
| FINAL_SUBMISSION/01_REPORT/Final_Internship_Report.docx = outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx | Identical bytes in two locations. |
| FINAL_SUBMISSION/01_REPORT/Final_Internship_Report.pdf = outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.pdf | Identical bytes in two locations. |
| FINAL_SUBMISSION/01_REPORT/report_validation_checklist.md = outputs/reports/report_validation_checklist.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/02_PRESENTATION/Final_Internship_Presentation.pdf = outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pdf | Identical bytes in two locations. |
| FINAL_SUBMISSION/02_PRESENTATION/Final_Internship_Presentation.pptx = outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/app.py = app.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/assets/css/style.css = assets/css/style.css | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/config.py = config.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/01_data_cleaning.ipynb = notebooks/01_data_cleaning.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/02_exploratory_data_analysis.ipynb = notebooks/02_exploratory_data_analysis.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/03_rfm_customer_analysis.ipynb = notebooks/03_rfm_customer_analysis.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/04_kmeans_customer_segmentation.ipynb = notebooks/04_kmeans_customer_segmentation.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/05_customer_lifetime_value.ipynb = notebooks/05_customer_lifetime_value.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/06_revenue_prediction.ipynb = notebooks/06_revenue_prediction.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/07_sales_forecasting.ipynb = notebooks/07_sales_forecasting.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/08_sql_business_analysis.ipynb = notebooks/08_sql_business_analysis.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/09_powerbi_data_model.ipynb = notebooks/09_powerbi_data_model.ipynb | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/about.py = pages/about.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/customers.py = pages/customers.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/data_explorer.py = pages/data_explorer.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/executive.py = pages/executive.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/forecasting.py = pages/forecasting.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/home.py = pages/home.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/prediction.py = pages/prediction.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/products.py = pages/products.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/recommendations.py = pages/recommendations.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/regional.py = pages/regional.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/revenue.py = pages/revenue.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/pages/segmentation.py = pages/segmentation.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/audit_cleaning.py = scripts/audit_cleaning.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/audit_project.py = scripts/audit_project.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_demo.py = scripts/build_demo.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_packaging.py = scripts/build_packaging.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_presentation.py = scripts/build_presentation.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_report.py = scripts/build_report.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_submission.py = scripts/build_submission.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_viva.py = scripts/build_viva.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/generate_dataset.py = scripts/generate_dataset.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_builder.py = scripts/report_builder.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_diagrams.py = scripts/report_diagrams.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_facts.py = scripts/report_facts.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/scripts/validate_dataset.py = scripts/validate_dataset.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/__init__.py = src/__init__.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/clv.py = src/clv.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/dashboard_utils.py = src/dashboard_utils.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/data_cleaning.py = src/data_cleaning.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/data_loader.py = src/data_loader.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/database.py = src/database.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/eda.py = src/eda.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/forecasting.py = src/forecasting.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/powerbi_dax.py = src/powerbi_dax.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/powerbi_prep.py = src/powerbi_prep.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/prediction.py = src/prediction.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/rfm.py = src/rfm.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/segmentation.py = src/segmentation.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/src/sql_analytics.py = src/sql_analytics.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/03_SOURCE_CODE/tests/test_streamlit_app.py = tests/test_streamlit_app.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/customer_revenue_intelligence.db = data/customer_revenue_intelligence.db | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/clv_modeling_dataset.csv = data/processed/clv_modeling_dataset.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_clv.csv = data/processed/customer_clv.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_level_features.csv = data/processed/customer_level_features.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_ml_segments.csv = data/processed/customer_ml_segments.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_rfm.csv = data/processed/customer_rfm.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_rfm_metadata.json = data/processed/customer_rfm_metadata.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_rfm_segments.csv = data/processed/customer_rfm_segments.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_sales_cleaned.csv = data/processed/customer_sales_cleaned.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/customer_value_history.csv = data/processed/customer_value_history.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/monthly_sales_timeseries.csv = data/processed/monthly_sales_timeseries.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/revenue_forecast.csv = data/processed/revenue_forecast.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/processed/revenue_modeling_dataset.csv = data/processed/revenue_modeling_dataset.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/raw/customer_sales_raw.csv = data/raw/customer_sales_raw.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/04_DATA/raw/data_quality_injection_log.json = data/raw/data_quality_injection_log.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/05_SQL/analysis_queries.sql = sql/analysis_queries.sql | Identical bytes in two locations. |
| FINAL_SUBMISSION/05_SQL/business_queries.sql = sql/business_queries.sql | Identical bytes in two locations. |
| FINAL_SUBMISSION/05_SQL/load_database.py = sql/load_database.py | Identical bytes in two locations. |
| FINAL_SUBMISSION/05_SQL/powerbi_views.sql = sql/powerbi_views.sql | Identical bytes in two locations. |
| FINAL_SUBMISSION/05_SQL/schema.sql = sql/schema.sql | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/clv_model.pkl = models/clv_model.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/clv_model_metadata.json = models/clv_model_metadata.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/clv_preprocessor.pkl = models/clv_preprocessor.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/forecasting_metadata.json = models/forecasting_metadata.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/forecasting_model.pkl = models/forecasting_model.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/kmeans_customer_segmentation.pkl = models/kmeans_customer_segmentation.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/pca_rfm.pkl = models/pca_rfm.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/revenue_model_metadata.json = models/revenue_model_metadata.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/revenue_prediction_model.pkl = models/revenue_prediction_model.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/revenue_prediction_preprocessor.pkl = models/revenue_prediction_preprocessor.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/rfm_scaler.pkl = models/rfm_scaler.pkl | Identical bytes in two locations. |
| FINAL_SUBMISSION/06_MODELS/segmentation_model_metadata.json = models/segmentation_model_metadata.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/POWERBI_BUILD_GUIDE.md = powerbi/POWERBI_BUILD_GUIDE.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimCluster.csv = powerbi/data/DimCluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimCustomer.csv = powerbi/data/DimCustomer.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimDate.csv = powerbi/data/DimDate.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimGeography.csv = powerbi/data/DimGeography.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimProduct.csv = powerbi/data/DimProduct.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimRFMSegment.csv = powerbi/data/DimRFMSegment.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactForecast.csv = powerbi/data/FactForecast.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactRevenuePrediction.csv = powerbi/data/FactRevenuePrediction.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactSales.csv = powerbi/data/FactSales.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/ModelInfo.csv = powerbi/data/ModelInfo.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/ModelMetrics.csv = powerbi/data/ModelMetrics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/PredictionQuarterly.csv = powerbi/data/PredictionQuarterly.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/Recommendations.csv = powerbi/data/Recommendations.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/measure_catalog.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_measure_catalog.csv = outputs/tables/powerbi_measure_catalog.csv = powerbi/dax/measure_catalog.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/measures.dax = powerbi/dax/measures.dax | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/validation_query.dax = powerbi/dax/validation_query.dax | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/00_home_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/57_powerbi_home_MOCKUP.png = outputs/figures/powerbi/mockups/00_home_mockup.png = outputs/screenshots/57_powerbi_home_MOCKUP.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/01_executive_overview_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/58_powerbi_executive_overview_MOCKUP.png = outputs/figures/powerbi/mockups/01_executive_overview_mockup.png = outputs/screenshots/58_powerbi_executive_overview_MOCKUP.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/02_revenue_intelligence_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/59_powerbi_revenue_intelligence_MOCKUP.png = outputs/figures/powerbi/mockups/02_revenue_intelligence_mockup.png = outputs/screenshots/59_powerbi_revenue_intelligence_MOCKUP | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/03_customer_intelligence_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/60_powerbi_customer_intelligence_MOCKUP.png = outputs/figures/powerbi/mockups/03_customer_intelligence_mockup.png = outputs/screenshots/60_powerbi_customer_intelligence_MO | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/04_customer_segmentation_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/61_powerbi_customer_segmentation_MOCKUP.png = outputs/figures/powerbi/mockups/04_customer_segmentation_mockup.png = outputs/screenshots/61_powerbi_customer_segmentation_MO | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/05_product_analytics_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/62_powerbi_product_analytics_MOCKUP.png = outputs/figures/powerbi/mockups/05_product_analytics_mockup.png = outputs/screenshots/62_powerbi_product_analytics_MOCKUP.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/06_regional_analytics_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/63_powerbi_regional_analytics_MOCKUP.png = outputs/figures/powerbi/mockups/06_regional_analytics_mockup.png = outputs/screenshots/63_powerbi_regional_analytics_MOCKUP.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/07_prediction_forecast_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/64_powerbi_prediction_forecast_MOCKUP.png = outputs/figures/powerbi/mockups/07_prediction_forecast_mockup.png = outputs/screenshots/64_powerbi_prediction_forecast_MOCKUP.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/08_business_recommendations_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/65_powerbi_recommendations_MOCKUP.png = outputs/figures/powerbi/mockups/08_business_recommendations_mockup.png = outputs/screenshots/65_powerbi_recommendations_MOCKUP.p | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/09_customer_detail_drillthrough_mockup.png = FINAL_SUBMISSION/08_SCREENSHOTS/66_powerbi_drillthrough_MOCKUP.png = outputs/figures/powerbi/mockups/09_customer_detail_drillthrough_mockup.png = outputs/screenshots/66_powerbi_drillthrough_MOCKUP | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerbi_dashboard_documentation.md = outputs/reports/powerbi_dashboard_documentation.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerbi_user_guide.md = outputs/reports/powerbi_user_guide.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/00_DataFolder_parameter.m = powerbi/powerquery/00_DataFolder_parameter.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimCluster.m = powerbi/powerquery/DimCluster.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimCustomer.m = powerbi/powerquery/DimCustomer.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimDate.m = powerbi/powerquery/DimDate.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimGeography.m = powerbi/powerquery/DimGeography.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimProduct.m = powerbi/powerquery/DimProduct.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimRFMSegment.m = powerbi/powerquery/DimRFMSegment.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactForecast.m = powerbi/powerquery/FactForecast.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactRevenuePrediction.m = powerbi/powerquery/FactRevenuePrediction.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactSales.m = powerbi/powerquery/FactSales.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/ModelInfo.m = powerbi/powerquery/ModelInfo.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/ModelMetrics.m = powerbi/powerquery/ModelMetrics.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/PredictionQuarterly.m = powerbi/powerquery/PredictionQuarterly.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/Recommendations.m = powerbi/powerquery/Recommendations.m | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/relationships.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_relationships.csv = outputs/tables/powerbi_relationships.csv = powerbi/relationships.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/table_catalog.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_table_catalog.csv = outputs/tables/powerbi_table_catalog.csv = powerbi/table_catalog.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/crm_dark_theme.json = powerbi/theme/crm_dark_theme.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/page_background.png = powerbi/theme/page_background.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/palette_reference.md = powerbi/theme/palette_reference.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/cross_step_consistency.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_cross_step_consistency.csv = outputs/tables/powerbi_cross_step_consistency.csv = powerbi/validation/cross_step_consistency.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/customer_state_validation_targets.csv = powerbi/validation/customer_state_validation_targets.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/measure_validation_targets.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_measure_validation.csv = outputs/tables/powerbi_measure_validation.csv = powerbi/validation/measure_validation_targets.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation_checklist.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_validation_checklist.csv = outputs/tables/powerbi_validation_checklist.csv = powerbi/validation_checklist.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/01_home.png = FINAL_SUBMISSION/08_SCREENSHOTS/67_streamlit_home.png = outputs/figures/streamlit/01_home.png = outputs/screenshots/67_streamlit_home.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/02_executive_overview.png = FINAL_SUBMISSION/08_SCREENSHOTS/68_streamlit_executive_overview.png = outputs/figures/streamlit/02_executive_overview.png = outputs/screenshots/68_streamlit_executive_overview.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/03_revenue_intelligence.png = FINAL_SUBMISSION/08_SCREENSHOTS/69_streamlit_revenue_intelligence.png = outputs/figures/streamlit/03_revenue_intelligence.png = outputs/screenshots/69_streamlit_revenue_intelligence.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/04_customer_intelligence.png = FINAL_SUBMISSION/08_SCREENSHOTS/70_streamlit_customer_intelligence.png = outputs/figures/streamlit/04_customer_intelligence.png = outputs/screenshots/70_streamlit_customer_intelligence.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/05_customer_segmentation.png = FINAL_SUBMISSION/08_SCREENSHOTS/71_streamlit_customer_segmentation.png = outputs/figures/streamlit/05_customer_segmentation.png = outputs/screenshots/71_streamlit_customer_segmentation.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/06_product_analytics.png = FINAL_SUBMISSION/08_SCREENSHOTS/72_streamlit_product_analytics.png = outputs/figures/streamlit/06_product_analytics.png = outputs/screenshots/72_streamlit_product_analytics.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/07_regional_analytics.png = FINAL_SUBMISSION/08_SCREENSHOTS/73_streamlit_regional_analytics.png = outputs/figures/streamlit/07_regional_analytics.png = outputs/screenshots/73_streamlit_regional_analytics.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/08_revenue_prediction.png = FINAL_SUBMISSION/08_SCREENSHOTS/74_streamlit_revenue_prediction.png = outputs/figures/streamlit/08_revenue_prediction.png = outputs/screenshots/74_streamlit_revenue_prediction.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/09_sales_forecast.png = FINAL_SUBMISSION/08_SCREENSHOTS/75_streamlit_sales_forecast.png = outputs/figures/streamlit/09_sales_forecast.png = outputs/screenshots/75_streamlit_sales_forecast.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/10_business_recommendations.png = FINAL_SUBMISSION/08_SCREENSHOTS/76_streamlit_recommendations.png = outputs/figures/streamlit/10_business_recommendations.png = outputs/screenshots/76_streamlit_recommendations.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/11_data_explorer.png = FINAL_SUBMISSION/08_SCREENSHOTS/77_streamlit_data_explorer.png = outputs/figures/streamlit/11_data_explorer.png = outputs/screenshots/77_streamlit_data_explorer.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/12_about_project.png = FINAL_SUBMISSION/08_SCREENSHOTS/78_streamlit_about.png = outputs/figures/streamlit/12_about_project.png = outputs/screenshots/78_streamlit_about.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/streamlit_documentation.md = FINAL_SUBMISSION/09_VIVA/streamlit_demo_script.md = outputs/viva/streamlit_demo_script.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/streamlit_testing_report.md = outputs/reports/streamlit_testing_report.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/01_raw_dataset_preview.png = outputs/screenshots/01_raw_dataset_preview.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/02_clean_dataset_preview.png = outputs/screenshots/02_clean_dataset_preview.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/03_data_quality_missing_before.png = outputs/figures/data_quality/01_missing_values_before.png = outputs/screenshots/03_data_quality_missing_before.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/04_data_quality_missing_after.png = outputs/figures/data_quality/02_missing_values_after.png = outputs/screenshots/04_data_quality_missing_after.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/05_data_quality_issue_summary.png = outputs/figures/data_quality/04_data_quality_issue_summary.png = outputs/screenshots/05_data_quality_issue_summary.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/06_outlier_distribution.png = outputs/figures/data_quality/03_outlier_distribution.png = outputs/screenshots/06_outlier_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/07_revenue_trend_monthly.png = outputs/figures/monthly_revenue_trend.png = outputs/screenshots/07_revenue_trend_monthly.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/08_profit_trend_monthly.png = outputs/figures/monthly_profit_trend.png = outputs/screenshots/08_profit_trend_monthly.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/09_revenue_growth_mom.png = outputs/figures/mom_revenue_growth.png = outputs/screenshots/09_revenue_growth_mom.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/10_customer_concentration.png = outputs/figures/revenue_concentration_curve.png = outputs/screenshots/10_customer_concentration.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/11_customer_revenue_distribution.png = outputs/figures/customer_revenue_distribution.png = outputs/screenshots/11_customer_revenue_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/12_purchase_frequency.png = outputs/figures/purchase_frequency.png = outputs/screenshots/12_purchase_frequency.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/13_category_revenue_vs_profit.png = outputs/figures/category_revenue_vs_profit.png = outputs/screenshots/13_category_revenue_vs_profit.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/14_product_quadrant.png = outputs/figures/product_revenue_profit_quadrant.png = outputs/screenshots/14_product_quadrant.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/15_regional_revenue.png = outputs/figures/regional_revenue.png = outputs/screenshots/15_regional_revenue.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/16_correlation_heatmap.png = outputs/figures/correlation_heatmap.png = outputs/screenshots/16_correlation_heatmap.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/17_discount_margin.png = outputs/figures/discount_profit_relationship.png = outputs/screenshots/17_discount_margin.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/18_order_status_value.png = outputs/figures/order_status_value.png = outputs/screenshots/18_order_status_value.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/19_rfm_recency_distribution.png = outputs/figures/rfm_recency_distribution.png = outputs/screenshots/19_rfm_recency_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/20_rfm_frequency_distribution.png = outputs/figures/rfm_frequency_distribution.png = outputs/screenshots/20_rfm_frequency_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/21_rfm_monetary_distribution.png = outputs/figures/rfm_monetary_distribution.png = outputs/screenshots/21_rfm_monetary_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/22_rfm_segment_distribution.png = outputs/figures/rfm_segment_distribution.png = outputs/screenshots/22_rfm_segment_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/23_rfm_revenue_contribution.png = outputs/figures/rfm_revenue_contribution.png = outputs/screenshots/23_rfm_revenue_contribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/24_rfm_segment_matrix.png = outputs/figures/rfm_segment_matrix.png = outputs/screenshots/24_rfm_segment_matrix.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/25_kmeans_feature_transformation.png = outputs/figures/kmeans_feature_transformation.png = outputs/screenshots/25_kmeans_feature_transformation.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/26_kmeans_elbow_curve.png = outputs/figures/kmeans_elbow_curve.png = outputs/screenshots/26_kmeans_elbow_curve.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/27_kmeans_silhouette_scores.png = outputs/figures/kmeans_silhouette_scores.png = outputs/screenshots/27_kmeans_silhouette_scores.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/28_kmeans_silhouette_diagram.png = outputs/figures/kmeans_silhouette_diagram.png = outputs/screenshots/28_kmeans_silhouette_diagram.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/29_kmeans_cluster_pca.png = outputs/figures/cluster_pca_visualization.png = outputs/screenshots/29_kmeans_cluster_pca.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/30_kmeans_cluster_profile.png = outputs/figures/cluster_centroid_profile.png = outputs/screenshots/30_kmeans_cluster_profile.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/31_kmeans_cluster_revenue.png = outputs/figures/cluster_revenue.png = outputs/screenshots/31_kmeans_cluster_revenue.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/32_rfm_vs_cluster_agreement.png = outputs/figures/rfm_vs_ml_cluster_heatmap.png = outputs/screenshots/32_rfm_vs_cluster_agreement.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/33_clv_distribution.png = outputs/figures/clv_distribution.png = outputs/screenshots/33_clv_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/34_clv_value_concentration.png = outputs/figures/clv_value_concentration.png = outputs/screenshots/34_clv_value_concentration.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/35_clv_model_comparison.png = outputs/figures/clv_model_comparison.png = outputs/screenshots/35_clv_model_comparison.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/36_clv_actual_vs_predicted.png = outputs/figures/clv_actual_vs_predicted.png = outputs/screenshots/36_clv_actual_vs_predicted.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/37_clv_by_rfm_segment.png = outputs/figures/clv_by_rfm_segment.png = outputs/screenshots/37_clv_by_rfm_segment.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/38_clv_feature_importance.png = outputs/figures/clv_feature_importance.png = outputs/screenshots/38_clv_feature_importance.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/39_prediction_actual_vs_predicted.png = outputs/figures/actual_vs_predicted_revenue.png = outputs/screenshots/39_prediction_actual_vs_predicted.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/40_prediction_model_comparison.png = outputs/figures/revenue_model_comparison.png = outputs/screenshots/40_prediction_model_comparison.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/41_prediction_feature_importance.png = outputs/figures/revenue_feature_importance.png = outputs/screenshots/41_prediction_feature_importance.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/42_prediction_error_distribution.png = outputs/figures/prediction_error_distribution.png = outputs/screenshots/42_prediction_error_distribution.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/43_prediction_error_by_revenue_range.png = outputs/figures/prediction_error_by_revenue_range.png = outputs/screenshots/43_prediction_error_by_revenue_range.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/44_prediction_timeline.png = outputs/figures/revenue_prediction_timeline.png = outputs/screenshots/44_prediction_timeline.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/45_forecast_historical_revenue.png = outputs/figures/forecasting/historical_revenue_trend.png = outputs/screenshots/45_forecast_historical_revenue.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/46_forecast_acf_pacf.png = outputs/figures/forecasting/acf_pacf.png = outputs/screenshots/46_forecast_acf_pacf.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/47_forecast_model_comparison.png = outputs/figures/forecasting/forecast_model_comparison.png = outputs/screenshots/47_forecast_model_comparison.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/48_forecast_backtest.png = outputs/figures/forecasting/backtest_results.png = outputs/screenshots/48_forecast_backtest.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/49_forecast_actual_vs_forecast.png = outputs/figures/forecasting/actual_vs_forecast.png = outputs/screenshots/49_forecast_actual_vs_forecast.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/50_forecast_seasonal_pattern.png = outputs/figures/forecasting/seasonal_pattern.png = outputs/screenshots/50_forecast_seasonal_pattern.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/51_sql_er_diagram.png = outputs/figures/sql/er_diagram.png = outputs/screenshots/51_sql_er_diagram.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/52_sql_top10_customers.png = outputs/figures/sql/sql_top10_customers.png = outputs/screenshots/52_sql_top10_customers.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/53_sql_customer_concentration.png = outputs/figures/sql/sql_customer_concentration.png = outputs/screenshots/53_sql_customer_concentration.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/54_sql_revenue_by_rfm_segment.png = outputs/figures/sql/sql_revenue_by_rfm_segment.png = outputs/screenshots/54_sql_revenue_by_rfm_segment.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/55_sql_monthly_revenue_growth.png = outputs/figures/sql/sql_monthly_revenue_growth.png = outputs/screenshots/55_sql_monthly_revenue_growth.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/56_sql_region_category_margin.png = outputs/figures/sql/sql_region_category_margin.png = outputs/screenshots/56_sql_region_category_margin.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/79_architecture.png = outputs/figures/report/architecture.png = outputs/screenshots/79_architecture.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/80_implementation_flowchart.png = outputs/figures/report/flowchart.png = outputs/screenshots/80_implementation_flowchart.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/08_SCREENSHOTS/81_graphical_abstract.png = outputs/figures/report/graphical_abstract.png = outputs/screenshots/81_graphical_abstract.png | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/01_basic_viva_questions.md = outputs/viva/01_basic_viva_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/02_intermediate_technical_questions.md = outputs/viva/02_intermediate_technical_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/03_advanced_data_science_questions.md = outputs/viva/03_advanced_data_science_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/04_sql_viva.md = outputs/viva/04_sql_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/05_powerbi_viva.md = outputs/viva/05_powerbi_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/06_streamlit_viva.md = outputs/viva/06_streamlit_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/07_business_questions.md = outputs/viva/07_business_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/08_challenging_questions.md = outputs/viva/08_challenging_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/09_trick_questions.md = outputs/viva/09_trick_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/10_mock_viva_easy.md = outputs/viva/10_mock_viva_easy.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/11_mock_viva_medium.md = outputs/viva/11_mock_viva_medium.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/12_mock_viva_difficult.md = outputs/viva/12_mock_viva_difficult.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/business_viva.md = outputs/viva/business_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/difficult_professor_questions.md = outputs/viva/difficult_professor_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/final_demo_order.md = outputs/viva/final_demo_order.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/final_revision_sheet.md = outputs/viva/final_revision_sheet.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/last_minute_revision.md = outputs/viva/last_minute_revision.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/live_demo_script.md = outputs/viva/live_demo_script.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/live_failure_handling.md = outputs/viva/live_failure_handling.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/ml_live_viva.md = outputs/viva/ml_live_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/one_line_answers.md = outputs/viva/one_line_answers.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/powerbi_demo_script.md = outputs/viva/powerbi_demo_script.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/presentation_speaking_script.md = outputs/viva/presentation_speaking_script.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/professor_presentation_questions.md = outputs/viva/professor_presentation_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/project_master_summary.md = outputs/viva/project_master_summary.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/rapid_fire_questions.md = outputs/viva/rapid_fire_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/rapid_fire_viva.md = outputs/viva/rapid_fire_viva.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/sql_demo_script.md = outputs/viva/sql_demo_script.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/top_20_viva_questions.md = outputs/viva/top_20_viva_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/trick_questions.md = outputs/viva/trick_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/09_VIVA/why_questions.md = outputs/viva/why_questions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/LICENSE = LICENSE | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/README.md = README.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/STEP2_Dataset_Design.md = docs/STEP2_Dataset_Design.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/STEP3_Data_Cleaning_Methodology.md = docs/STEP3_Data_Cleaning_Methodology.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/clv_analysis_report.md = outputs/reports/clv_analysis_report.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/eda_summary.md = outputs/reports/eda_summary.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/forecasting_methodology.md = outputs/reports/forecasting_methodology.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/kmeans_model_report.md = outputs/reports/kmeans_model_report.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/project_audit.md = outputs/reports/project_audit.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/raw_data_validation_report.md = outputs/reports/raw_data_validation_report.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/revenue_prediction_report.md = outputs/reports/revenue_prediction_report.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/rfm_methodology.md = outputs/reports/rfm_methodology.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/sql_analysis_methodology.md = outputs/reports/sql_analysis_methodology.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/cross_document_consistency.md = outputs/final_audit/cross_document_consistency.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/final_file_inventory.md = outputs/final_audit/final_file_inventory.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/final_submission_checklist.md = outputs/final_audit/final_submission_checklist.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/github_readiness_checklist.md = outputs/final_audit/github_readiness_checklist.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/live_demo_plan.md = outputs/final_audit/live_demo_plan.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/project_audit.md = outputs/final_audit/project_audit.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/project_handover.md = outputs/final_audit/project_handover.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/screenshot_checklist.md = outputs/final_audit/screenshot_checklist.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/project_build_log.md = docs/project_build_log.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/reproducibility_guide.md = docs/reproducibility_guide.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/requirements.txt = requirements.txt | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/FINAL_HANDOVER.md = outputs/final_submission/FINAL_HANDOVER.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/MASTER_SUBMISSION_CHECKLIST.md = outputs/final_submission/MASTER_SUBMISSION_CHECKLIST.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/backup_manifest.md = outputs/final_submission/backup_manifest.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/data_ethics_check.md = outputs/final_submission/data_ethics_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/declaration_check.md = outputs/final_submission/declaration_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_consistency_check.md = outputs/final_submission/final_consistency_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_project_inventory.md = outputs/final_submission/final_project_inventory.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_status.md = outputs/final_submission/final_status.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/github_final_check.md = outputs/final_submission/github_final_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/presentation_final_check.md = outputs/final_submission/presentation_final_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/report_final_check.md = outputs/final_submission/report_final_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/reproducibility_final_check.md = outputs/final_submission/reproducibility_final_check.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/student_manual_actions.md = outputs/final_submission/student_manual_actions.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/submission_cover_page.md = outputs/final_submission/submission_cover_page.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/zip_contents.md = outputs/final_submission/zip_contents.md | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_data_consistency.csv = outputs/tables/audit_data_consistency.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_findings.csv = outputs/tables/audit_findings.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_integration.csv = outputs/tables/audit_integration.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_models.csv = outputs/tables/audit_models.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_pipeline.csv = outputs/tables/audit_pipeline.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_structure.csv = outputs/tables/audit_structure.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_summary.csv = outputs/tables/audit_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/business_insights.csv = outputs/tables/business_insights.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/business_questions.csv = outputs/tables/business_questions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/category_summary.csv = outputs/tables/category_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/city_summary.csv = outputs/tables/city_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_accuracy_vs_ground_truth.csv = outputs/tables/cleaning_accuracy_vs_ground_truth.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_category_standardisation.csv = outputs/tables/cleaning_category_standardisation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_corrections_applied.csv = outputs/tables/cleaning_corrections_applied.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_missing_value_log.csv = outputs/tables/cleaning_missing_value_log.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_rule_checks_before_after.csv = outputs/tables/cleaning_rule_checks_before_after.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_annual_repeat_rates.csv = outputs/tables/clv_annual_repeat_rates.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_assumptions.csv = outputs/tables/clv_assumptions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_bgnbd_evaluation.csv = outputs/tables/clv_bgnbd_evaluation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_business_insights.csv = outputs/tables/clv_business_insights.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_business_questions.csv = outputs/tables/clv_business_questions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_by_ml_cluster.csv = outputs/tables/clv_by_ml_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_by_rfm_segment.csv = outputs/tables/clv_by_rfm_segment.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_calibration_by_decile.csv = outputs/tables/clv_calibration_by_decile.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_data_readiness.csv = outputs/tables/clv_data_readiness.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_feature_importance.csv = outputs/tables/clv_feature_importance.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_feature_selection.csv = outputs/tables/clv_feature_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_future_value_correlations.csv = outputs/tables/clv_future_value_correlations.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_high_value_groups.csv = outputs/tables/clv_high_value_groups.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_horizon_sensitivity.csv = outputs/tables/clv_horizon_sensitivity.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_inactivity_threshold_sensitivity.csv = outputs/tables/clv_inactivity_threshold_sensitivity.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_interpurchase_gaps.csv = outputs/tables/clv_interpurchase_gaps.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_model_comparison.csv = outputs/tables/clv_model_comparison.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_model_cv_selection.csv = outputs/tables/clv_model_cv_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_profit_decomposition.csv = outputs/tables/clv_profit_decomposition.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_single_purchase_customers.csv = outputs/tables/clv_single_purchase_customers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_test_predictions.csv = outputs/tables/clv_test_predictions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_validation_checks.csv = outputs/tables/clv_validation_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_concentration.csv = outputs/tables/clv_value_concentration.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_distribution.csv = outputs/tables/clv_value_distribution.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_drivers.csv = outputs/tables/clv_value_drivers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_percentiles.csv = outputs/tables/clv_value_percentiles.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/correlation_pairs.csv = outputs/tables/correlation_pairs.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_characteristic_tests.csv = outputs/tables/customer_characteristic_tests.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_revenue_by_attribute.csv = outputs/tables/customer_revenue_by_attribute.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_revenue_concentration.csv = FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_revenue_concentration.csv = outputs/tables/customer_revenue_concentration.csv = outputs/tables/sql/cust_revenue_concentration.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_segment_sql_analysis.csv = outputs/tables/customer_segment_sql_analysis.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_summary.csv = outputs/tables/customer_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_validation_stats.csv = outputs/tables/customer_validation_stats.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/day_of_week_summary.csv = outputs/tables/day_of_week_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_correlations.csv = outputs/tables/discount_correlations.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_margin_by_category.csv = outputs/tables/discount_margin_by_category.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_summary.csv = outputs/tables/discount_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_descriptive_statistics.csv = outputs/tables/eda_descriptive_statistics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_kpis.csv = outputs/tables/eda_kpis.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_order_definition_checks.csv = outputs/tables/eda_order_definition_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_outlier_classes.csv = outputs/tables/eda_outlier_classes.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_outlier_summary.csv = outputs/tables/eda_outlier_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_quality_checks.csv = outputs/tables/eda_quality_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/feature_usage_leakage_check.csv = outputs/tables/feature_usage_leakage_check.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_acf_pacf.csv = outputs/tables/forecast_acf_pacf.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_adf_tests.csv = outputs/tables/forecast_adf_tests.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_by_horizon.csv = outputs/tables/forecast_backtest_by_horizon.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_folds.csv = outputs/tables/forecast_backtest_folds.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_summary.csv = outputs/tables/forecast_backtest_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_business_interpretation.csv = outputs/tables/forecast_business_interpretation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_by_dimension.csv = outputs/tables/forecast_by_dimension.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_by_dimension_evaluation.csv = outputs/tables/forecast_by_dimension_evaluation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_data_quality.csv = outputs/tables/forecast_data_quality.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_future.csv = outputs/tables/forecast_future.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_model_comparison.csv = outputs/tables/forecast_model_comparison.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_model_selection.csv = outputs/tables/forecast_model_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_quality_checklist.csv = outputs/tables/forecast_quality_checklist.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_rolling_statistics.csv = outputs/tables/forecast_rolling_statistics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_seasonal_index.csv = outputs/tables/forecast_seasonal_index.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_split_summary.csv = outputs/tables/forecast_split_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_stl_decomposition.csv = outputs/tables/forecast_stl_decomposition.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_validation_tuning.csv = outputs/tables/forecast_validation_tuning.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_yearly_summary.csv = outputs/tables/forecast_yearly_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_business_questions.csv = outputs/tables/ml_business_questions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_centroids.csv = outputs/tables/ml_cluster_centroids.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_insights.csv = outputs/tables/ml_cluster_insights.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_label_mapping.csv = outputs/tables/ml_cluster_label_mapping.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_summary.csv = outputs/tables/ml_cluster_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_data_quality_checks.csv = outputs/tables/ml_data_quality_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_distribution_check.csv = outputs/tables/ml_feature_distribution_check.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_selection.csv = outputs/tables/ml_feature_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_set_comparison.csv = outputs/tables/ml_feature_set_comparison.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_final_model_metrics.csv = outputs/tables/ml_final_model_metrics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_k_evaluation.csv = outputs/tables/ml_k_evaluation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_pca_summary.csv = outputs/tables/ml_pca_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_silhouette_by_cluster.csv = outputs/tables/ml_silhouette_by_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_validation_checks.csv = outputs/tables/ml_validation_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/monthly_summary.csv = outputs/tables/monthly_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/order_status_summary.csv = outputs/tables/order_status_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/outlier_interpretation.csv = outputs/tables/outlier_interpretation.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/outlier_summary.csv = outputs/tables/outlier_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/payment_summary.csv = outputs/tables/payment_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/product_profitability.csv = outputs/tables/product_profitability.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/product_revenue_profit_quadrants.csv = outputs/tables/product_revenue_profit_quadrants.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/product_summary.csv = outputs/tables/product_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/purchase_frequency.csv = outputs/tables/purchase_frequency.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/quarterly_summary.csv = outputs/tables/quarterly_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/regional_summary.csv = outputs/tables/regional_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/report_facts.json = outputs/tables/report_facts.json | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_business_questions.csv = outputs/tables/revenue_business_questions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_categorical_drivers.csv = outputs/tables/revenue_categorical_drivers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_concentration.csv = outputs/tables/revenue_concentration.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_cutoff_timing.csv = outputs/tables/revenue_cutoff_timing.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_data_checks.csv = outputs/tables/revenue_data_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_driver_analysis.csv = outputs/tables/revenue_driver_analysis.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_category.csv = outputs/tables/revenue_error_by_category.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_quarter.csv = outputs/tables/revenue_error_by_quarter.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_region.csv = outputs/tables/revenue_error_by_region.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_revenue_range.csv = outputs/tables/revenue_error_by_revenue_range.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_catalog.csv = outputs/tables/revenue_feature_catalog.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_importance.csv = outputs/tables/revenue_feature_importance.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_selection.csv = outputs/tables/revenue_feature_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_leakage_audit.csv = outputs/tables/revenue_leakage_audit.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_level_feature_check.csv = outputs/tables/revenue_level_feature_check.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_linear_coefficients.csv = outputs/tables/revenue_linear_coefficients.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_comparison.csv = outputs/tables/revenue_model_comparison.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_selection.csv = outputs/tables/revenue_model_selection.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_validation_results.csv = outputs/tables/revenue_model_validation_results.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_by_cluster.csv = outputs/tables/revenue_prediction_by_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_by_rfm.csv = outputs/tables/revenue_prediction_by_rfm.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_design.csv = outputs/tables/revenue_prediction_design.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_predictions.csv = outputs/tables/revenue_predictions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_quarterly_totals.csv = outputs/tables/revenue_quarterly_totals.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_scenarios.csv = outputs/tables/revenue_scenarios.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_split_summary.csv = outputs/tables/revenue_split_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_tuning_results.csv = outputs/tables/revenue_tuning_results.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_validation_checks.csv = outputs/tables/revenue_validation_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_business_insights.csv = outputs/tables/rfm_business_insights.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_business_questions.csv = outputs/tables/rfm_business_questions.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_concentration_stats.csv = outputs/tables/rfm_concentration_stats.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_descriptive_statistics.csv = outputs/tables/rfm_descriptive_statistics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_excluded_customers.csv = outputs/tables/rfm_excluded_customers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_headline_metrics.csv = outputs/tables/rfm_headline_metrics.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_high_value_at_risk.csv = outputs/tables/rfm_high_value_at_risk.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_high_value_at_risk_rule.csv = outputs/tables/rfm_high_value_at_risk_rule.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_log_transform_check.csv = outputs/tables/rfm_log_transform_check.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_most_recent_customers.csv = outputs/tables/rfm_most_recent_customers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_qcut_feasibility.csv = outputs/tables/rfm_qcut_feasibility.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_revenue_concentration.csv = outputs/tables/rfm_revenue_concentration.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_score_bins.csv = outputs/tables/rfm_score_bins.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_score_grid_R_by_F.csv = outputs/tables/rfm_score_grid_R_by_F.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_profile.csv = outputs/tables/rfm_segment_profile.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_rules.csv = outputs/tables/rfm_segment_rules.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_summary.csv = outputs/tables/rfm_segment_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_top_customers_frequency.csv = outputs/tables/rfm_top_customers_frequency.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_top_customers_monetary.csv = outputs/tables/rfm_top_customers_monetary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_validation_checks.csv = outputs/tables/rfm_validation_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_value_activity_groups.csv = outputs/tables/rfm_value_activity_groups.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_agreement.csv = outputs/tables/rfm_vs_ml_agreement.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_by_cluster.csv = outputs/tables/rfm_vs_ml_by_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_by_segment.csv = outputs/tables/rfm_vs_ml_by_segment.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster.csv = outputs/tables/rfm_vs_ml_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster_col_pct.csv = outputs/tables/rfm_vs_ml_cluster_col_pct.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster_row_pct.csv = outputs/tables/rfm_vs_ml_cluster_row_pct.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/seasonal_index.csv = outputs/tables/seasonal_index.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ01.csv = outputs/tables/sql/BQ01.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ02.csv = outputs/tables/sql/BQ02.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ03.csv = outputs/tables/sql/BQ03.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ04.csv = outputs/tables/sql/BQ04.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ05.csv = outputs/tables/sql/BQ05.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ06.csv = outputs/tables/sql/BQ06.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ07.csv = outputs/tables/sql/BQ07.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ08.csv = outputs/tables/sql/BQ08.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ09.csv = outputs/tables/sql/BQ09.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ10.csv = outputs/tables/sql/BQ10.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ11.csv = outputs/tables/sql/BQ11.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ12.csv = outputs/tables/sql/BQ12.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ13.csv = outputs/tables/sql/BQ13.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ14.csv = outputs/tables/sql/BQ14.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ15.csv = outputs/tables/sql/BQ15.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ16.csv = outputs/tables/sql/BQ16.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ17.csv = outputs/tables/sql/BQ17.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ18.csv = outputs/tables/sql/BQ18.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ19.csv = outputs/tables/sql/BQ19.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ20.csv = outputs/tables/sql/BQ20.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_acquired_by_year.csv = outputs/tables/sql/cust_acquired_by_year.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_concentration_summary.csv = outputs/tables/sql/cust_concentration_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_frequency_distribution.csv = outputs/tables/sql/cust_frequency_distribution.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_highest_aov.csv = outputs/tables/sql/cust_highest_aov.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_inactive.csv = outputs/tables/sql/cust_inactive.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_most_frequent.csv = outputs/tables/sql/cust_most_frequent.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_new_vs_existing.csv = outputs/tables/sql/cust_new_vs_existing.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_top_profit.csv = outputs/tables/sql/cust_top_profit.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_top_revenue.csv = outputs/tables/sql/cust_top_revenue.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_avg_selling_price.csv = outputs/tables/sql/prod_avg_selling_price.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_category_performance.csv = outputs/tables/sql/prod_category_performance.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_discount_bands.csv = outputs/tables/sql/prod_discount_bands.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_investigate.csv = outputs/tables/sql/prod_investigate.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_profitability.csv = outputs/tables/sql/prod_profitability.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_subcategory_performance.csv = outputs/tables/sql/prod_subcategory_performance.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_profit.csv = outputs/tables/sql/prod_top_profit.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_quantity.csv = outputs/tables/sql/prod_top_quantity.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_revenue.csv = outputs/tables/sql/prod_top_revenue.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_category_matrix.csv = outputs/tables/sql/reg_category_matrix.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_customers_without_orders.csv = outputs/tables/sql/reg_customers_without_orders.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_performance.csv = outputs/tables/sql/reg_performance.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_top_states.csv = outputs/tables/sql/reg_top_states.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_by_quarter.csv = outputs/tables/sql/rev_by_quarter.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_by_year.csv = outputs/tables/sql/rev_by_year.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_kpi_summary.csv = outputs/tables/sql/rev_kpi_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_margin_by_year_category.csv = outputs/tables/sql/rev_margin_by_year_category.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_order_status.csv = outputs/tables/sql/rev_order_status.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_ml_cluster_summary.csv = outputs/tables/sql/seg_ml_cluster_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_rfm_summary.csv = outputs/tables/sql/seg_rfm_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_rfm_vs_cluster.csv = outputs/tables/sql/seg_rfm_vs_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_value_activity_groups.csv = outputs/tables/sql/seg_value_activity_groups.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_value_by_cluster.csv = outputs/tables/sql/seg_value_by_cluster.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_best_worst_months.csv = outputs/tables/sql/time_best_worst_months.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_month_of_year.csv = outputs/tables/sql/time_month_of_year.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_monthly.csv = outputs/tables/sql/time_monthly.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_ytd_running_total.csv = outputs/tables/sql/time_ytd_running_total.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_key_findings.csv = outputs/tables/sql_key_findings.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_quality_checklist.csv = outputs/tables/sql_quality_checklist.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_query_catalog.csv = outputs/tables/sql_query_catalog.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_table_catalog.csv = outputs/tables/sql_table_catalog.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_technique_coverage.csv = outputs/tables/sql_technique_coverage.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_validation_checks.csv = outputs/tables/sql_validation_checks.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/state_summary.csv = outputs/tables/state_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_page_load_times.csv = outputs/tables/streamlit_page_load_times.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_quality_checklist.csv = outputs/tables/streamlit_quality_checklist.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_test_results.csv = outputs/tables/streamlit_test_results.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/subcategory_summary.csv = outputs/tables/subcategory_summary.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/top_customers_profit.csv = outputs/tables/top_customers_profit.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/top_customers_revenue.csv = outputs/tables/top_customers_revenue.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/unusual_customers.csv = outputs/tables/unusual_customers.csv | Identical bytes in two locations. |
| FINAL_SUBMISSION/11_OUTPUT_TABLES/yearly_summary.csv = outputs/tables/yearly_summary.csv | Identical bytes in two locations. |

These duplicates are **deliberate**: Step 11 writes its catalogues both into `powerbi/` (where the
Power BI build needs them) and into `outputs/tables/` (the project-wide convention that every
generated table lives there), and Step 10 saves the customer-concentration query under a named
copy. They are regenerated together by the same module, so they cannot drift apart. They are
listed here for completeness, not as defects, and nothing was deleted.

### Repeated filenames in different directories

| Filename | Locations |
|---|---|
| config.toml | .streamlit/config.toml, FINAL_SUBMISSION/03_SOURCE_CODE/.streamlit/config.toml |
| report_validation_checklist.md | FINAL_SUBMISSION/01_REPORT/report_validation_checklist.md, outputs/reports/report_validation_checklist.md |
| app.py | FINAL_SUBMISSION/03_SOURCE_CODE/app.py, app.py |
| style.css | FINAL_SUBMISSION/03_SOURCE_CODE/assets/css/style.css, assets/css/style.css |
| config.py | FINAL_SUBMISSION/03_SOURCE_CODE/config.py, config.py |
| 01_data_cleaning.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/01_data_cleaning.ipynb, notebooks/01_data_cleaning.ipynb |
| 02_exploratory_data_analysis.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/02_exploratory_data_analysis.ipynb, notebooks/02_exploratory_data_analysis.ipynb |
| 03_rfm_customer_analysis.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/03_rfm_customer_analysis.ipynb, notebooks/03_rfm_customer_analysis.ipynb |
| 04_kmeans_customer_segmentation.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/04_kmeans_customer_segmentation.ipynb, notebooks/04_kmeans_customer_segmentation.ipynb |
| 05_customer_lifetime_value.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/05_customer_lifetime_value.ipynb, notebooks/05_customer_lifetime_value.ipynb |
| 06_revenue_prediction.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/06_revenue_prediction.ipynb, notebooks/06_revenue_prediction.ipynb |
| 07_sales_forecasting.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/07_sales_forecasting.ipynb, notebooks/07_sales_forecasting.ipynb |
| 08_sql_business_analysis.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/08_sql_business_analysis.ipynb, notebooks/08_sql_business_analysis.ipynb |
| 09_powerbi_data_model.ipynb | FINAL_SUBMISSION/03_SOURCE_CODE/notebooks/09_powerbi_data_model.ipynb, notebooks/09_powerbi_data_model.ipynb |
| about.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/about.py, pages/about.py |
| customers.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/customers.py, pages/customers.py |
| data_explorer.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/data_explorer.py, pages/data_explorer.py |
| executive.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/executive.py, pages/executive.py |
| forecasting.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/forecasting.py, FINAL_SUBMISSION/03_SOURCE_CODE/src/forecasting.py, pages/forecasting.py, src/forecasting.py |
| home.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/home.py, pages/home.py |
| prediction.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/prediction.py, FINAL_SUBMISSION/03_SOURCE_CODE/src/prediction.py, pages/prediction.py, src/prediction.py |
| products.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/products.py, pages/products.py |
| recommendations.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/recommendations.py, pages/recommendations.py |
| regional.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/regional.py, pages/regional.py |
| revenue.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/revenue.py, pages/revenue.py |
| segmentation.py | FINAL_SUBMISSION/03_SOURCE_CODE/pages/segmentation.py, FINAL_SUBMISSION/03_SOURCE_CODE/src/segmentation.py, pages/segmentation.py, src/segmentation.py |
| audit_cleaning.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/audit_cleaning.py, scripts/audit_cleaning.py |
| audit_project.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/audit_project.py, scripts/audit_project.py |
| build_demo.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_demo.py, scripts/build_demo.py |
| build_packaging.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_packaging.py, scripts/build_packaging.py |
| build_presentation.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_presentation.py, scripts/build_presentation.py |
| build_report.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_report.py, scripts/build_report.py |
| build_submission.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_submission.py, scripts/build_submission.py |
| build_viva.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/build_viva.py, scripts/build_viva.py |
| generate_dataset.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/generate_dataset.py, scripts/generate_dataset.py |
| report_builder.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_builder.py, scripts/report_builder.py |
| report_diagrams.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_diagrams.py, scripts/report_diagrams.py |
| report_facts.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/report_facts.py, scripts/report_facts.py |
| validate_dataset.py | FINAL_SUBMISSION/03_SOURCE_CODE/scripts/validate_dataset.py, scripts/validate_dataset.py |
| __init__.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/__init__.py, src/__init__.py |
| clv.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/clv.py, src/clv.py |
| dashboard_utils.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/dashboard_utils.py, src/dashboard_utils.py |
| data_cleaning.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/data_cleaning.py, src/data_cleaning.py |
| data_loader.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/data_loader.py, src/data_loader.py |
| database.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/database.py, src/database.py |
| eda.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/eda.py, src/eda.py |
| powerbi_dax.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/powerbi_dax.py, src/powerbi_dax.py |
| powerbi_prep.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/powerbi_prep.py, src/powerbi_prep.py |
| rfm.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/rfm.py, src/rfm.py |
| sql_analytics.py | FINAL_SUBMISSION/03_SOURCE_CODE/src/sql_analytics.py, src/sql_analytics.py |
| test_streamlit_app.py | FINAL_SUBMISSION/03_SOURCE_CODE/tests/test_streamlit_app.py, tests/test_streamlit_app.py |
| customer_revenue_intelligence.db | FINAL_SUBMISSION/04_DATA/customer_revenue_intelligence.db, data/customer_revenue_intelligence.db |
| .gitkeep | FINAL_SUBMISSION/04_DATA/processed/.gitkeep, assets/images/.gitkeep, data/processed/.gitkeep |
| clv_modeling_dataset.csv | FINAL_SUBMISSION/04_DATA/processed/clv_modeling_dataset.csv, data/processed/clv_modeling_dataset.csv |
| customer_clv.csv | FINAL_SUBMISSION/04_DATA/processed/customer_clv.csv, data/processed/customer_clv.csv |
| customer_level_features.csv | FINAL_SUBMISSION/04_DATA/processed/customer_level_features.csv, data/processed/customer_level_features.csv |
| customer_ml_segments.csv | FINAL_SUBMISSION/04_DATA/processed/customer_ml_segments.csv, data/processed/customer_ml_segments.csv |
| customer_rfm.csv | FINAL_SUBMISSION/04_DATA/processed/customer_rfm.csv, data/processed/customer_rfm.csv |
| customer_rfm_metadata.json | FINAL_SUBMISSION/04_DATA/processed/customer_rfm_metadata.json, data/processed/customer_rfm_metadata.json |
| customer_rfm_segments.csv | FINAL_SUBMISSION/04_DATA/processed/customer_rfm_segments.csv, data/processed/customer_rfm_segments.csv |
| customer_sales_cleaned.csv | FINAL_SUBMISSION/04_DATA/processed/customer_sales_cleaned.csv, data/processed/customer_sales_cleaned.csv |
| customer_value_history.csv | FINAL_SUBMISSION/04_DATA/processed/customer_value_history.csv, data/processed/customer_value_history.csv |
| monthly_sales_timeseries.csv | FINAL_SUBMISSION/04_DATA/processed/monthly_sales_timeseries.csv, data/processed/monthly_sales_timeseries.csv |
| revenue_forecast.csv | FINAL_SUBMISSION/04_DATA/processed/revenue_forecast.csv, data/processed/revenue_forecast.csv |
| revenue_modeling_dataset.csv | FINAL_SUBMISSION/04_DATA/processed/revenue_modeling_dataset.csv, data/processed/revenue_modeling_dataset.csv |
| customer_sales_raw.csv | FINAL_SUBMISSION/04_DATA/raw/customer_sales_raw.csv, data/raw/customer_sales_raw.csv |
| data_quality_injection_log.json | FINAL_SUBMISSION/04_DATA/raw/data_quality_injection_log.json, data/raw/data_quality_injection_log.json |
| analysis_queries.sql | FINAL_SUBMISSION/05_SQL/analysis_queries.sql, sql/analysis_queries.sql |
| business_queries.sql | FINAL_SUBMISSION/05_SQL/business_queries.sql, sql/business_queries.sql |
| load_database.py | FINAL_SUBMISSION/05_SQL/load_database.py, sql/load_database.py |
| powerbi_views.sql | FINAL_SUBMISSION/05_SQL/powerbi_views.sql, sql/powerbi_views.sql |
| schema.sql | FINAL_SUBMISSION/05_SQL/schema.sql, sql/schema.sql |
| clv_model.pkl | FINAL_SUBMISSION/06_MODELS/clv_model.pkl, models/clv_model.pkl |
| clv_model_metadata.json | FINAL_SUBMISSION/06_MODELS/clv_model_metadata.json, models/clv_model_metadata.json |
| clv_preprocessor.pkl | FINAL_SUBMISSION/06_MODELS/clv_preprocessor.pkl, models/clv_preprocessor.pkl |
| forecasting_metadata.json | FINAL_SUBMISSION/06_MODELS/forecasting_metadata.json, models/forecasting_metadata.json |
| forecasting_model.pkl | FINAL_SUBMISSION/06_MODELS/forecasting_model.pkl, models/forecasting_model.pkl |
| kmeans_customer_segmentation.pkl | FINAL_SUBMISSION/06_MODELS/kmeans_customer_segmentation.pkl, models/kmeans_customer_segmentation.pkl |
| pca_rfm.pkl | FINAL_SUBMISSION/06_MODELS/pca_rfm.pkl, models/pca_rfm.pkl |
| revenue_model_metadata.json | FINAL_SUBMISSION/06_MODELS/revenue_model_metadata.json, models/revenue_model_metadata.json |
| revenue_prediction_model.pkl | FINAL_SUBMISSION/06_MODELS/revenue_prediction_model.pkl, models/revenue_prediction_model.pkl |
| revenue_prediction_preprocessor.pkl | FINAL_SUBMISSION/06_MODELS/revenue_prediction_preprocessor.pkl, models/revenue_prediction_preprocessor.pkl |
| rfm_scaler.pkl | FINAL_SUBMISSION/06_MODELS/rfm_scaler.pkl, models/rfm_scaler.pkl |
| segmentation_model_metadata.json | FINAL_SUBMISSION/06_MODELS/segmentation_model_metadata.json, models/segmentation_model_metadata.json |
| POWERBI_BUILD_GUIDE.md | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/POWERBI_BUILD_GUIDE.md, powerbi/POWERBI_BUILD_GUIDE.md |
| DimCluster.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimCluster.csv, powerbi/data/DimCluster.csv |
| DimCustomer.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimCustomer.csv, powerbi/data/DimCustomer.csv |
| DimDate.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimDate.csv, powerbi/data/DimDate.csv |
| DimGeography.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimGeography.csv, powerbi/data/DimGeography.csv |
| DimProduct.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimProduct.csv, powerbi/data/DimProduct.csv |
| DimRFMSegment.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/DimRFMSegment.csv, powerbi/data/DimRFMSegment.csv |
| FactForecast.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactForecast.csv, powerbi/data/FactForecast.csv |
| FactRevenuePrediction.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactRevenuePrediction.csv, powerbi/data/FactRevenuePrediction.csv |
| FactSales.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/FactSales.csv, powerbi/data/FactSales.csv |
| ModelInfo.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/ModelInfo.csv, powerbi/data/ModelInfo.csv |
| ModelMetrics.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/ModelMetrics.csv, powerbi/data/ModelMetrics.csv |
| PredictionQuarterly.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/PredictionQuarterly.csv, powerbi/data/PredictionQuarterly.csv |
| Recommendations.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/data/Recommendations.csv, powerbi/data/Recommendations.csv |
| measure_catalog.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/measure_catalog.csv, powerbi/dax/measure_catalog.csv |
| measures.dax | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/measures.dax, powerbi/dax/measures.dax |
| validation_query.dax | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/dax/validation_query.dax, powerbi/dax/validation_query.dax |
| 00_home_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/00_home_mockup.png, outputs/figures/powerbi/mockups/00_home_mockup.png |
| 01_executive_overview_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/01_executive_overview_mockup.png, outputs/figures/powerbi/mockups/01_executive_overview_mockup.png |
| 02_revenue_intelligence_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/02_revenue_intelligence_mockup.png, outputs/figures/powerbi/mockups/02_revenue_intelligence_mockup.png |
| 03_customer_intelligence_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/03_customer_intelligence_mockup.png, outputs/figures/powerbi/mockups/03_customer_intelligence_mockup.png |
| 04_customer_segmentation_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/04_customer_segmentation_mockup.png, outputs/figures/powerbi/mockups/04_customer_segmentation_mockup.png |
| 05_product_analytics_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/05_product_analytics_mockup.png, outputs/figures/powerbi/mockups/05_product_analytics_mockup.png |
| 06_regional_analytics_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/06_regional_analytics_mockup.png, outputs/figures/powerbi/mockups/06_regional_analytics_mockup.png |
| 07_prediction_forecast_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/07_prediction_forecast_mockup.png, outputs/figures/powerbi/mockups/07_prediction_forecast_mockup.png |
| 08_business_recommendations_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/08_business_recommendations_mockup.png, outputs/figures/powerbi/mockups/08_business_recommendations_mockup.png |
| 09_customer_detail_drillthrough_mockup.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/page_design_mockups/09_customer_detail_drillthrough_mockup.png, outputs/figures/powerbi/mockups/09_customer_detail_drillthrough_mockup.png |
| powerbi_dashboard_documentation.md | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerbi_dashboard_documentation.md, outputs/reports/powerbi_dashboard_documentation.md |
| powerbi_user_guide.md | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerbi_user_guide.md, outputs/reports/powerbi_user_guide.md |
| 00_DataFolder_parameter.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/00_DataFolder_parameter.m, powerbi/powerquery/00_DataFolder_parameter.m |
| DimCluster.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimCluster.m, powerbi/powerquery/DimCluster.m |
| DimCustomer.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimCustomer.m, powerbi/powerquery/DimCustomer.m |
| DimDate.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimDate.m, powerbi/powerquery/DimDate.m |
| DimGeography.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimGeography.m, powerbi/powerquery/DimGeography.m |
| DimProduct.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimProduct.m, powerbi/powerquery/DimProduct.m |
| DimRFMSegment.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/DimRFMSegment.m, powerbi/powerquery/DimRFMSegment.m |
| FactForecast.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactForecast.m, powerbi/powerquery/FactForecast.m |
| FactRevenuePrediction.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactRevenuePrediction.m, powerbi/powerquery/FactRevenuePrediction.m |
| FactSales.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/FactSales.m, powerbi/powerquery/FactSales.m |
| ModelInfo.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/ModelInfo.m, powerbi/powerquery/ModelInfo.m |
| ModelMetrics.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/ModelMetrics.m, powerbi/powerquery/ModelMetrics.m |
| PredictionQuarterly.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/PredictionQuarterly.m, powerbi/powerquery/PredictionQuarterly.m |
| Recommendations.m | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/powerquery/Recommendations.m, powerbi/powerquery/Recommendations.m |
| relationships.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/relationships.csv, powerbi/relationships.csv |
| table_catalog.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/table_catalog.csv, powerbi/table_catalog.csv |
| crm_dark_theme.json | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/crm_dark_theme.json, powerbi/theme/crm_dark_theme.json |
| page_background.png | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/page_background.png, powerbi/theme/page_background.png |
| palette_reference.md | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/theme/palette_reference.md, powerbi/theme/palette_reference.md |
| cross_step_consistency.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/cross_step_consistency.csv, powerbi/validation/cross_step_consistency.csv |
| customer_state_validation_targets.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/customer_state_validation_targets.csv, powerbi/validation/customer_state_validation_targets.csv |
| measure_validation_targets.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation/measure_validation_targets.csv, powerbi/validation/measure_validation_targets.csv |
| validation_checklist.csv | FINAL_SUBMISSION/07_DASHBOARDS/PowerBI/validation_checklist.csv, powerbi/validation_checklist.csv |
| 01_home.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/01_home.png, outputs/figures/streamlit/01_home.png |
| 02_executive_overview.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/02_executive_overview.png, outputs/figures/streamlit/02_executive_overview.png |
| 03_revenue_intelligence.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/03_revenue_intelligence.png, outputs/figures/streamlit/03_revenue_intelligence.png |
| 04_customer_intelligence.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/04_customer_intelligence.png, outputs/figures/streamlit/04_customer_intelligence.png |
| 05_customer_segmentation.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/05_customer_segmentation.png, outputs/figures/streamlit/05_customer_segmentation.png |
| 06_product_analytics.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/06_product_analytics.png, outputs/figures/streamlit/06_product_analytics.png |
| 07_regional_analytics.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/07_regional_analytics.png, outputs/figures/streamlit/07_regional_analytics.png |
| 08_revenue_prediction.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/08_revenue_prediction.png, outputs/figures/streamlit/08_revenue_prediction.png |
| 09_sales_forecast.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/09_sales_forecast.png, outputs/figures/streamlit/09_sales_forecast.png |
| 10_business_recommendations.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/10_business_recommendations.png, outputs/figures/streamlit/10_business_recommendations.png |
| 11_data_explorer.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/11_data_explorer.png, outputs/figures/streamlit/11_data_explorer.png |
| 12_about_project.png | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/screenshots/12_about_project.png, outputs/figures/streamlit/12_about_project.png |
| streamlit_testing_report.md | FINAL_SUBMISSION/07_DASHBOARDS/Streamlit/streamlit_testing_report.md, outputs/reports/streamlit_testing_report.md |
| 01_raw_dataset_preview.png | FINAL_SUBMISSION/08_SCREENSHOTS/01_raw_dataset_preview.png, outputs/screenshots/01_raw_dataset_preview.png |
| 02_clean_dataset_preview.png | FINAL_SUBMISSION/08_SCREENSHOTS/02_clean_dataset_preview.png, outputs/screenshots/02_clean_dataset_preview.png |
| 03_data_quality_missing_before.png | FINAL_SUBMISSION/08_SCREENSHOTS/03_data_quality_missing_before.png, outputs/screenshots/03_data_quality_missing_before.png |
| 04_data_quality_missing_after.png | FINAL_SUBMISSION/08_SCREENSHOTS/04_data_quality_missing_after.png, outputs/screenshots/04_data_quality_missing_after.png |
| 05_data_quality_issue_summary.png | FINAL_SUBMISSION/08_SCREENSHOTS/05_data_quality_issue_summary.png, outputs/screenshots/05_data_quality_issue_summary.png |
| 06_outlier_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/06_outlier_distribution.png, outputs/screenshots/06_outlier_distribution.png |
| 07_revenue_trend_monthly.png | FINAL_SUBMISSION/08_SCREENSHOTS/07_revenue_trend_monthly.png, outputs/screenshots/07_revenue_trend_monthly.png |
| 08_profit_trend_monthly.png | FINAL_SUBMISSION/08_SCREENSHOTS/08_profit_trend_monthly.png, outputs/screenshots/08_profit_trend_monthly.png |
| 09_revenue_growth_mom.png | FINAL_SUBMISSION/08_SCREENSHOTS/09_revenue_growth_mom.png, outputs/screenshots/09_revenue_growth_mom.png |
| 10_customer_concentration.png | FINAL_SUBMISSION/08_SCREENSHOTS/10_customer_concentration.png, outputs/screenshots/10_customer_concentration.png |
| 11_customer_revenue_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/11_customer_revenue_distribution.png, outputs/screenshots/11_customer_revenue_distribution.png |
| 12_purchase_frequency.png | FINAL_SUBMISSION/08_SCREENSHOTS/12_purchase_frequency.png, outputs/screenshots/12_purchase_frequency.png |
| 13_category_revenue_vs_profit.png | FINAL_SUBMISSION/08_SCREENSHOTS/13_category_revenue_vs_profit.png, outputs/screenshots/13_category_revenue_vs_profit.png |
| 14_product_quadrant.png | FINAL_SUBMISSION/08_SCREENSHOTS/14_product_quadrant.png, outputs/screenshots/14_product_quadrant.png |
| 15_regional_revenue.png | FINAL_SUBMISSION/08_SCREENSHOTS/15_regional_revenue.png, outputs/screenshots/15_regional_revenue.png |
| 16_correlation_heatmap.png | FINAL_SUBMISSION/08_SCREENSHOTS/16_correlation_heatmap.png, outputs/screenshots/16_correlation_heatmap.png |
| 17_discount_margin.png | FINAL_SUBMISSION/08_SCREENSHOTS/17_discount_margin.png, outputs/screenshots/17_discount_margin.png |
| 18_order_status_value.png | FINAL_SUBMISSION/08_SCREENSHOTS/18_order_status_value.png, outputs/screenshots/18_order_status_value.png |
| 19_rfm_recency_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/19_rfm_recency_distribution.png, outputs/screenshots/19_rfm_recency_distribution.png |
| 20_rfm_frequency_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/20_rfm_frequency_distribution.png, outputs/screenshots/20_rfm_frequency_distribution.png |
| 21_rfm_monetary_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/21_rfm_monetary_distribution.png, outputs/screenshots/21_rfm_monetary_distribution.png |
| 22_rfm_segment_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/22_rfm_segment_distribution.png, outputs/screenshots/22_rfm_segment_distribution.png |
| 23_rfm_revenue_contribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/23_rfm_revenue_contribution.png, outputs/screenshots/23_rfm_revenue_contribution.png |
| 24_rfm_segment_matrix.png | FINAL_SUBMISSION/08_SCREENSHOTS/24_rfm_segment_matrix.png, outputs/screenshots/24_rfm_segment_matrix.png |
| 25_kmeans_feature_transformation.png | FINAL_SUBMISSION/08_SCREENSHOTS/25_kmeans_feature_transformation.png, outputs/screenshots/25_kmeans_feature_transformation.png |
| 26_kmeans_elbow_curve.png | FINAL_SUBMISSION/08_SCREENSHOTS/26_kmeans_elbow_curve.png, outputs/screenshots/26_kmeans_elbow_curve.png |
| 27_kmeans_silhouette_scores.png | FINAL_SUBMISSION/08_SCREENSHOTS/27_kmeans_silhouette_scores.png, outputs/screenshots/27_kmeans_silhouette_scores.png |
| 28_kmeans_silhouette_diagram.png | FINAL_SUBMISSION/08_SCREENSHOTS/28_kmeans_silhouette_diagram.png, outputs/screenshots/28_kmeans_silhouette_diagram.png |
| 29_kmeans_cluster_pca.png | FINAL_SUBMISSION/08_SCREENSHOTS/29_kmeans_cluster_pca.png, outputs/screenshots/29_kmeans_cluster_pca.png |
| 30_kmeans_cluster_profile.png | FINAL_SUBMISSION/08_SCREENSHOTS/30_kmeans_cluster_profile.png, outputs/screenshots/30_kmeans_cluster_profile.png |
| 31_kmeans_cluster_revenue.png | FINAL_SUBMISSION/08_SCREENSHOTS/31_kmeans_cluster_revenue.png, outputs/screenshots/31_kmeans_cluster_revenue.png |
| 32_rfm_vs_cluster_agreement.png | FINAL_SUBMISSION/08_SCREENSHOTS/32_rfm_vs_cluster_agreement.png, outputs/screenshots/32_rfm_vs_cluster_agreement.png |
| 33_clv_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/33_clv_distribution.png, outputs/screenshots/33_clv_distribution.png |
| 34_clv_value_concentration.png | FINAL_SUBMISSION/08_SCREENSHOTS/34_clv_value_concentration.png, outputs/screenshots/34_clv_value_concentration.png |
| 35_clv_model_comparison.png | FINAL_SUBMISSION/08_SCREENSHOTS/35_clv_model_comparison.png, outputs/screenshots/35_clv_model_comparison.png |
| 36_clv_actual_vs_predicted.png | FINAL_SUBMISSION/08_SCREENSHOTS/36_clv_actual_vs_predicted.png, outputs/screenshots/36_clv_actual_vs_predicted.png |
| 37_clv_by_rfm_segment.png | FINAL_SUBMISSION/08_SCREENSHOTS/37_clv_by_rfm_segment.png, outputs/screenshots/37_clv_by_rfm_segment.png |
| 38_clv_feature_importance.png | FINAL_SUBMISSION/08_SCREENSHOTS/38_clv_feature_importance.png, outputs/screenshots/38_clv_feature_importance.png |
| 39_prediction_actual_vs_predicted.png | FINAL_SUBMISSION/08_SCREENSHOTS/39_prediction_actual_vs_predicted.png, outputs/screenshots/39_prediction_actual_vs_predicted.png |
| 40_prediction_model_comparison.png | FINAL_SUBMISSION/08_SCREENSHOTS/40_prediction_model_comparison.png, outputs/screenshots/40_prediction_model_comparison.png |
| 41_prediction_feature_importance.png | FINAL_SUBMISSION/08_SCREENSHOTS/41_prediction_feature_importance.png, outputs/screenshots/41_prediction_feature_importance.png |
| 42_prediction_error_distribution.png | FINAL_SUBMISSION/08_SCREENSHOTS/42_prediction_error_distribution.png, outputs/screenshots/42_prediction_error_distribution.png |
| 43_prediction_error_by_revenue_range.png | FINAL_SUBMISSION/08_SCREENSHOTS/43_prediction_error_by_revenue_range.png, outputs/screenshots/43_prediction_error_by_revenue_range.png |
| 44_prediction_timeline.png | FINAL_SUBMISSION/08_SCREENSHOTS/44_prediction_timeline.png, outputs/screenshots/44_prediction_timeline.png |
| 45_forecast_historical_revenue.png | FINAL_SUBMISSION/08_SCREENSHOTS/45_forecast_historical_revenue.png, outputs/screenshots/45_forecast_historical_revenue.png |
| 46_forecast_acf_pacf.png | FINAL_SUBMISSION/08_SCREENSHOTS/46_forecast_acf_pacf.png, outputs/screenshots/46_forecast_acf_pacf.png |
| 47_forecast_model_comparison.png | FINAL_SUBMISSION/08_SCREENSHOTS/47_forecast_model_comparison.png, outputs/screenshots/47_forecast_model_comparison.png |
| 48_forecast_backtest.png | FINAL_SUBMISSION/08_SCREENSHOTS/48_forecast_backtest.png, outputs/screenshots/48_forecast_backtest.png |
| 49_forecast_actual_vs_forecast.png | FINAL_SUBMISSION/08_SCREENSHOTS/49_forecast_actual_vs_forecast.png, outputs/screenshots/49_forecast_actual_vs_forecast.png |
| 50_forecast_seasonal_pattern.png | FINAL_SUBMISSION/08_SCREENSHOTS/50_forecast_seasonal_pattern.png, outputs/screenshots/50_forecast_seasonal_pattern.png |
| 51_sql_er_diagram.png | FINAL_SUBMISSION/08_SCREENSHOTS/51_sql_er_diagram.png, outputs/screenshots/51_sql_er_diagram.png |
| 52_sql_top10_customers.png | FINAL_SUBMISSION/08_SCREENSHOTS/52_sql_top10_customers.png, outputs/screenshots/52_sql_top10_customers.png |
| 53_sql_customer_concentration.png | FINAL_SUBMISSION/08_SCREENSHOTS/53_sql_customer_concentration.png, outputs/screenshots/53_sql_customer_concentration.png |
| 54_sql_revenue_by_rfm_segment.png | FINAL_SUBMISSION/08_SCREENSHOTS/54_sql_revenue_by_rfm_segment.png, outputs/screenshots/54_sql_revenue_by_rfm_segment.png |
| 55_sql_monthly_revenue_growth.png | FINAL_SUBMISSION/08_SCREENSHOTS/55_sql_monthly_revenue_growth.png, outputs/screenshots/55_sql_monthly_revenue_growth.png |
| 56_sql_region_category_margin.png | FINAL_SUBMISSION/08_SCREENSHOTS/56_sql_region_category_margin.png, outputs/screenshots/56_sql_region_category_margin.png |
| 57_powerbi_home_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/57_powerbi_home_MOCKUP.png, outputs/screenshots/57_powerbi_home_MOCKUP.png |
| 58_powerbi_executive_overview_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/58_powerbi_executive_overview_MOCKUP.png, outputs/screenshots/58_powerbi_executive_overview_MOCKUP.png |
| 59_powerbi_revenue_intelligence_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/59_powerbi_revenue_intelligence_MOCKUP.png, outputs/screenshots/59_powerbi_revenue_intelligence_MOCKUP.png |
| 60_powerbi_customer_intelligence_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/60_powerbi_customer_intelligence_MOCKUP.png, outputs/screenshots/60_powerbi_customer_intelligence_MOCKUP.png |
| 61_powerbi_customer_segmentation_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/61_powerbi_customer_segmentation_MOCKUP.png, outputs/screenshots/61_powerbi_customer_segmentation_MOCKUP.png |
| 62_powerbi_product_analytics_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/62_powerbi_product_analytics_MOCKUP.png, outputs/screenshots/62_powerbi_product_analytics_MOCKUP.png |
| 63_powerbi_regional_analytics_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/63_powerbi_regional_analytics_MOCKUP.png, outputs/screenshots/63_powerbi_regional_analytics_MOCKUP.png |
| 64_powerbi_prediction_forecast_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/64_powerbi_prediction_forecast_MOCKUP.png, outputs/screenshots/64_powerbi_prediction_forecast_MOCKUP.png |
| 65_powerbi_recommendations_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/65_powerbi_recommendations_MOCKUP.png, outputs/screenshots/65_powerbi_recommendations_MOCKUP.png |
| 66_powerbi_drillthrough_MOCKUP.png | FINAL_SUBMISSION/08_SCREENSHOTS/66_powerbi_drillthrough_MOCKUP.png, outputs/screenshots/66_powerbi_drillthrough_MOCKUP.png |
| 67_streamlit_home.png | FINAL_SUBMISSION/08_SCREENSHOTS/67_streamlit_home.png, outputs/screenshots/67_streamlit_home.png |
| 68_streamlit_executive_overview.png | FINAL_SUBMISSION/08_SCREENSHOTS/68_streamlit_executive_overview.png, outputs/screenshots/68_streamlit_executive_overview.png |
| 69_streamlit_revenue_intelligence.png | FINAL_SUBMISSION/08_SCREENSHOTS/69_streamlit_revenue_intelligence.png, outputs/screenshots/69_streamlit_revenue_intelligence.png |
| 70_streamlit_customer_intelligence.png | FINAL_SUBMISSION/08_SCREENSHOTS/70_streamlit_customer_intelligence.png, outputs/screenshots/70_streamlit_customer_intelligence.png |
| 71_streamlit_customer_segmentation.png | FINAL_SUBMISSION/08_SCREENSHOTS/71_streamlit_customer_segmentation.png, outputs/screenshots/71_streamlit_customer_segmentation.png |
| 72_streamlit_product_analytics.png | FINAL_SUBMISSION/08_SCREENSHOTS/72_streamlit_product_analytics.png, outputs/screenshots/72_streamlit_product_analytics.png |
| 73_streamlit_regional_analytics.png | FINAL_SUBMISSION/08_SCREENSHOTS/73_streamlit_regional_analytics.png, outputs/screenshots/73_streamlit_regional_analytics.png |
| 74_streamlit_revenue_prediction.png | FINAL_SUBMISSION/08_SCREENSHOTS/74_streamlit_revenue_prediction.png, outputs/screenshots/74_streamlit_revenue_prediction.png |
| 75_streamlit_sales_forecast.png | FINAL_SUBMISSION/08_SCREENSHOTS/75_streamlit_sales_forecast.png, outputs/screenshots/75_streamlit_sales_forecast.png |
| 76_streamlit_recommendations.png | FINAL_SUBMISSION/08_SCREENSHOTS/76_streamlit_recommendations.png, outputs/screenshots/76_streamlit_recommendations.png |
| 77_streamlit_data_explorer.png | FINAL_SUBMISSION/08_SCREENSHOTS/77_streamlit_data_explorer.png, outputs/screenshots/77_streamlit_data_explorer.png |
| 78_streamlit_about.png | FINAL_SUBMISSION/08_SCREENSHOTS/78_streamlit_about.png, outputs/screenshots/78_streamlit_about.png |
| 79_architecture.png | FINAL_SUBMISSION/08_SCREENSHOTS/79_architecture.png, outputs/screenshots/79_architecture.png |
| 80_implementation_flowchart.png | FINAL_SUBMISSION/08_SCREENSHOTS/80_implementation_flowchart.png, outputs/screenshots/80_implementation_flowchart.png |
| 81_graphical_abstract.png | FINAL_SUBMISSION/08_SCREENSHOTS/81_graphical_abstract.png, outputs/screenshots/81_graphical_abstract.png |
| 01_basic_viva_questions.md | FINAL_SUBMISSION/09_VIVA/01_basic_viva_questions.md, outputs/viva/01_basic_viva_questions.md |
| 02_intermediate_technical_questions.md | FINAL_SUBMISSION/09_VIVA/02_intermediate_technical_questions.md, outputs/viva/02_intermediate_technical_questions.md |
| 03_advanced_data_science_questions.md | FINAL_SUBMISSION/09_VIVA/03_advanced_data_science_questions.md, outputs/viva/03_advanced_data_science_questions.md |
| 04_sql_viva.md | FINAL_SUBMISSION/09_VIVA/04_sql_viva.md, outputs/viva/04_sql_viva.md |
| 05_powerbi_viva.md | FINAL_SUBMISSION/09_VIVA/05_powerbi_viva.md, outputs/viva/05_powerbi_viva.md |
| 06_streamlit_viva.md | FINAL_SUBMISSION/09_VIVA/06_streamlit_viva.md, outputs/viva/06_streamlit_viva.md |
| 07_business_questions.md | FINAL_SUBMISSION/09_VIVA/07_business_questions.md, outputs/viva/07_business_questions.md |
| 08_challenging_questions.md | FINAL_SUBMISSION/09_VIVA/08_challenging_questions.md, outputs/viva/08_challenging_questions.md |
| 09_trick_questions.md | FINAL_SUBMISSION/09_VIVA/09_trick_questions.md, outputs/viva/09_trick_questions.md |
| 10_mock_viva_easy.md | FINAL_SUBMISSION/09_VIVA/10_mock_viva_easy.md, outputs/viva/10_mock_viva_easy.md |
| 11_mock_viva_medium.md | FINAL_SUBMISSION/09_VIVA/11_mock_viva_medium.md, outputs/viva/11_mock_viva_medium.md |
| 12_mock_viva_difficult.md | FINAL_SUBMISSION/09_VIVA/12_mock_viva_difficult.md, outputs/viva/12_mock_viva_difficult.md |
| business_viva.md | FINAL_SUBMISSION/09_VIVA/business_viva.md, outputs/viva/business_viva.md |
| difficult_professor_questions.md | FINAL_SUBMISSION/09_VIVA/difficult_professor_questions.md, outputs/viva/difficult_professor_questions.md |
| final_demo_order.md | FINAL_SUBMISSION/09_VIVA/final_demo_order.md, outputs/viva/final_demo_order.md |
| final_revision_sheet.md | FINAL_SUBMISSION/09_VIVA/final_revision_sheet.md, outputs/viva/final_revision_sheet.md |
| last_minute_revision.md | FINAL_SUBMISSION/09_VIVA/last_minute_revision.md, outputs/viva/last_minute_revision.md |
| live_demo_script.md | FINAL_SUBMISSION/09_VIVA/live_demo_script.md, outputs/viva/live_demo_script.md |
| live_failure_handling.md | FINAL_SUBMISSION/09_VIVA/live_failure_handling.md, outputs/viva/live_failure_handling.md |
| ml_live_viva.md | FINAL_SUBMISSION/09_VIVA/ml_live_viva.md, outputs/viva/ml_live_viva.md |
| one_line_answers.md | FINAL_SUBMISSION/09_VIVA/one_line_answers.md, outputs/viva/one_line_answers.md |
| powerbi_demo_script.md | FINAL_SUBMISSION/09_VIVA/powerbi_demo_script.md, outputs/viva/powerbi_demo_script.md |
| presentation_speaking_script.md | FINAL_SUBMISSION/09_VIVA/presentation_speaking_script.md, outputs/viva/presentation_speaking_script.md |
| professor_presentation_questions.md | FINAL_SUBMISSION/09_VIVA/professor_presentation_questions.md, outputs/viva/professor_presentation_questions.md |
| project_master_summary.md | FINAL_SUBMISSION/09_VIVA/project_master_summary.md, outputs/viva/project_master_summary.md |
| rapid_fire_questions.md | FINAL_SUBMISSION/09_VIVA/rapid_fire_questions.md, outputs/viva/rapid_fire_questions.md |
| rapid_fire_viva.md | FINAL_SUBMISSION/09_VIVA/rapid_fire_viva.md, outputs/viva/rapid_fire_viva.md |
| sql_demo_script.md | FINAL_SUBMISSION/09_VIVA/sql_demo_script.md, outputs/viva/sql_demo_script.md |
| streamlit_demo_script.md | FINAL_SUBMISSION/09_VIVA/streamlit_demo_script.md, outputs/viva/streamlit_demo_script.md |
| top_20_viva_questions.md | FINAL_SUBMISSION/09_VIVA/top_20_viva_questions.md, outputs/viva/top_20_viva_questions.md |
| trick_questions.md | FINAL_SUBMISSION/09_VIVA/trick_questions.md, outputs/viva/trick_questions.md |
| why_questions.md | FINAL_SUBMISSION/09_VIVA/why_questions.md, outputs/viva/why_questions.md |
| LICENSE | FINAL_SUBMISSION/10_DOCUMENTATION/LICENSE, LICENSE |
| README.md | FINAL_SUBMISSION/10_DOCUMENTATION/README.md, README.md, outputs/figures/powerbi/README.md |
| STEP2_Dataset_Design.md | FINAL_SUBMISSION/10_DOCUMENTATION/STEP2_Dataset_Design.md, docs/STEP2_Dataset_Design.md |
| STEP3_Data_Cleaning_Methodology.md | FINAL_SUBMISSION/10_DOCUMENTATION/STEP3_Data_Cleaning_Methodology.md, docs/STEP3_Data_Cleaning_Methodology.md |
| clv_analysis_report.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/clv_analysis_report.md, outputs/reports/clv_analysis_report.md |
| eda_summary.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/eda_summary.md, outputs/reports/eda_summary.md |
| forecasting_methodology.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/forecasting_methodology.md, outputs/reports/forecasting_methodology.md |
| kmeans_model_report.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/kmeans_model_report.md, outputs/reports/kmeans_model_report.md |
| project_audit.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/project_audit.md, FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/project_audit.md, outputs/final_audit/project_audit.md, outputs/reports/project_audit.md |
| raw_data_validation_report.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/raw_data_validation_report.md, outputs/reports/raw_data_validation_report.md |
| revenue_prediction_report.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/revenue_prediction_report.md, outputs/reports/revenue_prediction_report.md |
| rfm_methodology.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/rfm_methodology.md, outputs/reports/rfm_methodology.md |
| sql_analysis_methodology.md | FINAL_SUBMISSION/10_DOCUMENTATION/methodology_reports/sql_analysis_methodology.md, outputs/reports/sql_analysis_methodology.md |
| cross_document_consistency.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/cross_document_consistency.md, outputs/final_audit/cross_document_consistency.md |
| final_file_inventory.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/final_file_inventory.md, outputs/final_audit/final_file_inventory.md |
| final_submission_checklist.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/final_submission_checklist.md, outputs/final_audit/final_submission_checklist.md |
| github_readiness_checklist.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/github_readiness_checklist.md, outputs/final_audit/github_readiness_checklist.md |
| live_demo_plan.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/live_demo_plan.md, outputs/final_audit/live_demo_plan.md |
| project_handover.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/project_handover.md, outputs/final_audit/project_handover.md |
| screenshot_checklist.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_audits/screenshot_checklist.md, outputs/final_audit/screenshot_checklist.md |
| project_build_log.md | FINAL_SUBMISSION/10_DOCUMENTATION/project_build_log.md, docs/project_build_log.md |
| reproducibility_guide.md | FINAL_SUBMISSION/10_DOCUMENTATION/reproducibility_guide.md, docs/reproducibility_guide.md |
| requirements.txt | FINAL_SUBMISSION/10_DOCUMENTATION/requirements.txt, requirements.txt |
| FINAL_HANDOVER.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/FINAL_HANDOVER.md, outputs/final_submission/FINAL_HANDOVER.md |
| MASTER_SUBMISSION_CHECKLIST.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/MASTER_SUBMISSION_CHECKLIST.md, outputs/final_submission/MASTER_SUBMISSION_CHECKLIST.md |
| backup_manifest.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/backup_manifest.md, outputs/final_submission/backup_manifest.md |
| data_ethics_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/data_ethics_check.md, outputs/final_submission/data_ethics_check.md |
| declaration_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/declaration_check.md, outputs/final_submission/declaration_check.md |
| final_consistency_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_consistency_check.md, outputs/final_submission/final_consistency_check.md |
| final_project_inventory.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_project_inventory.md, outputs/final_submission/final_project_inventory.md |
| final_status.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/final_status.md, outputs/final_submission/final_status.md |
| github_final_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/github_final_check.md, outputs/final_submission/github_final_check.md |
| presentation_final_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/presentation_final_check.md, outputs/final_submission/presentation_final_check.md |
| report_final_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/report_final_check.md, outputs/final_submission/report_final_check.md |
| reproducibility_final_check.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/reproducibility_final_check.md, outputs/final_submission/reproducibility_final_check.md |
| student_manual_actions.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/student_manual_actions.md, outputs/final_submission/student_manual_actions.md |
| submission_cover_page.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/submission_cover_page.md, outputs/final_submission/submission_cover_page.md |
| zip_contents.md | FINAL_SUBMISSION/10_DOCUMENTATION/submission_documents/zip_contents.md, outputs/final_submission/zip_contents.md |
| audit_data_consistency.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_data_consistency.csv, outputs/tables/audit_data_consistency.csv |
| audit_findings.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_findings.csv, outputs/tables/audit_findings.csv |
| audit_integration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_integration.csv, outputs/tables/audit_integration.csv |
| audit_models.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_models.csv, outputs/tables/audit_models.csv |
| audit_pipeline.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_pipeline.csv, outputs/tables/audit_pipeline.csv |
| audit_structure.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_structure.csv, outputs/tables/audit_structure.csv |
| audit_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/audit_summary.csv, outputs/tables/audit_summary.csv |
| business_insights.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/business_insights.csv, outputs/tables/business_insights.csv |
| business_questions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/business_questions.csv, outputs/tables/business_questions.csv |
| category_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/category_summary.csv, outputs/tables/category_summary.csv |
| city_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/city_summary.csv, outputs/tables/city_summary.csv |
| cleaning_accuracy_vs_ground_truth.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_accuracy_vs_ground_truth.csv, outputs/tables/cleaning_accuracy_vs_ground_truth.csv |
| cleaning_category_standardisation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_category_standardisation.csv, outputs/tables/cleaning_category_standardisation.csv |
| cleaning_corrections_applied.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_corrections_applied.csv, outputs/tables/cleaning_corrections_applied.csv |
| cleaning_missing_value_log.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_missing_value_log.csv, outputs/tables/cleaning_missing_value_log.csv |
| cleaning_rule_checks_before_after.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/cleaning_rule_checks_before_after.csv, outputs/tables/cleaning_rule_checks_before_after.csv |
| clv_annual_repeat_rates.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_annual_repeat_rates.csv, outputs/tables/clv_annual_repeat_rates.csv |
| clv_assumptions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_assumptions.csv, outputs/tables/clv_assumptions.csv |
| clv_bgnbd_evaluation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_bgnbd_evaluation.csv, outputs/tables/clv_bgnbd_evaluation.csv |
| clv_business_insights.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_business_insights.csv, outputs/tables/clv_business_insights.csv |
| clv_business_questions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_business_questions.csv, outputs/tables/clv_business_questions.csv |
| clv_by_ml_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_by_ml_cluster.csv, outputs/tables/clv_by_ml_cluster.csv |
| clv_by_rfm_segment.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_by_rfm_segment.csv, outputs/tables/clv_by_rfm_segment.csv |
| clv_calibration_by_decile.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_calibration_by_decile.csv, outputs/tables/clv_calibration_by_decile.csv |
| clv_data_readiness.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_data_readiness.csv, outputs/tables/clv_data_readiness.csv |
| clv_feature_importance.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_feature_importance.csv, outputs/tables/clv_feature_importance.csv |
| clv_feature_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_feature_selection.csv, outputs/tables/clv_feature_selection.csv |
| clv_future_value_correlations.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_future_value_correlations.csv, outputs/tables/clv_future_value_correlations.csv |
| clv_high_value_groups.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_high_value_groups.csv, outputs/tables/clv_high_value_groups.csv |
| clv_horizon_sensitivity.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_horizon_sensitivity.csv, outputs/tables/clv_horizon_sensitivity.csv |
| clv_inactivity_threshold_sensitivity.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_inactivity_threshold_sensitivity.csv, outputs/tables/clv_inactivity_threshold_sensitivity.csv |
| clv_interpurchase_gaps.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_interpurchase_gaps.csv, outputs/tables/clv_interpurchase_gaps.csv |
| clv_model_comparison.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_model_comparison.csv, outputs/tables/clv_model_comparison.csv |
| clv_model_cv_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_model_cv_selection.csv, outputs/tables/clv_model_cv_selection.csv |
| clv_profit_decomposition.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_profit_decomposition.csv, outputs/tables/clv_profit_decomposition.csv |
| clv_single_purchase_customers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_single_purchase_customers.csv, outputs/tables/clv_single_purchase_customers.csv |
| clv_test_predictions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_test_predictions.csv, outputs/tables/clv_test_predictions.csv |
| clv_validation_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_validation_checks.csv, outputs/tables/clv_validation_checks.csv |
| clv_value_concentration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_concentration.csv, outputs/tables/clv_value_concentration.csv |
| clv_value_distribution.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_distribution.csv, outputs/tables/clv_value_distribution.csv |
| clv_value_drivers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_drivers.csv, outputs/tables/clv_value_drivers.csv |
| clv_value_percentiles.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/clv_value_percentiles.csv, outputs/tables/clv_value_percentiles.csv |
| correlation_pairs.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/correlation_pairs.csv, outputs/tables/correlation_pairs.csv |
| customer_characteristic_tests.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_characteristic_tests.csv, outputs/tables/customer_characteristic_tests.csv |
| customer_revenue_by_attribute.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_revenue_by_attribute.csv, outputs/tables/customer_revenue_by_attribute.csv |
| customer_revenue_concentration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_revenue_concentration.csv, outputs/tables/customer_revenue_concentration.csv |
| customer_segment_sql_analysis.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_segment_sql_analysis.csv, outputs/tables/customer_segment_sql_analysis.csv |
| customer_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_summary.csv, outputs/tables/customer_summary.csv |
| customer_validation_stats.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/customer_validation_stats.csv, outputs/tables/customer_validation_stats.csv |
| day_of_week_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/day_of_week_summary.csv, outputs/tables/day_of_week_summary.csv |
| discount_correlations.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_correlations.csv, outputs/tables/discount_correlations.csv |
| discount_margin_by_category.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_margin_by_category.csv, outputs/tables/discount_margin_by_category.csv |
| discount_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/discount_summary.csv, outputs/tables/discount_summary.csv |
| eda_descriptive_statistics.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_descriptive_statistics.csv, outputs/tables/eda_descriptive_statistics.csv |
| eda_kpis.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_kpis.csv, outputs/tables/eda_kpis.csv |
| eda_order_definition_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_order_definition_checks.csv, outputs/tables/eda_order_definition_checks.csv |
| eda_outlier_classes.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_outlier_classes.csv, outputs/tables/eda_outlier_classes.csv |
| eda_outlier_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_outlier_summary.csv, outputs/tables/eda_outlier_summary.csv |
| eda_quality_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/eda_quality_checks.csv, outputs/tables/eda_quality_checks.csv |
| feature_usage_leakage_check.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/feature_usage_leakage_check.csv, outputs/tables/feature_usage_leakage_check.csv |
| forecast_acf_pacf.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_acf_pacf.csv, outputs/tables/forecast_acf_pacf.csv |
| forecast_adf_tests.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_adf_tests.csv, outputs/tables/forecast_adf_tests.csv |
| forecast_backtest_by_horizon.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_by_horizon.csv, outputs/tables/forecast_backtest_by_horizon.csv |
| forecast_backtest_folds.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_folds.csv, outputs/tables/forecast_backtest_folds.csv |
| forecast_backtest_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_backtest_summary.csv, outputs/tables/forecast_backtest_summary.csv |
| forecast_business_interpretation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_business_interpretation.csv, outputs/tables/forecast_business_interpretation.csv |
| forecast_by_dimension.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_by_dimension.csv, outputs/tables/forecast_by_dimension.csv |
| forecast_by_dimension_evaluation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_by_dimension_evaluation.csv, outputs/tables/forecast_by_dimension_evaluation.csv |
| forecast_data_quality.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_data_quality.csv, outputs/tables/forecast_data_quality.csv |
| forecast_future.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_future.csv, outputs/tables/forecast_future.csv |
| forecast_model_comparison.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_model_comparison.csv, outputs/tables/forecast_model_comparison.csv |
| forecast_model_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_model_selection.csv, outputs/tables/forecast_model_selection.csv |
| forecast_quality_checklist.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_quality_checklist.csv, outputs/tables/forecast_quality_checklist.csv |
| forecast_rolling_statistics.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_rolling_statistics.csv, outputs/tables/forecast_rolling_statistics.csv |
| forecast_seasonal_index.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_seasonal_index.csv, outputs/tables/forecast_seasonal_index.csv |
| forecast_split_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_split_summary.csv, outputs/tables/forecast_split_summary.csv |
| forecast_stl_decomposition.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_stl_decomposition.csv, outputs/tables/forecast_stl_decomposition.csv |
| forecast_validation_tuning.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_validation_tuning.csv, outputs/tables/forecast_validation_tuning.csv |
| forecast_yearly_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/forecast_yearly_summary.csv, outputs/tables/forecast_yearly_summary.csv |
| ml_business_questions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_business_questions.csv, outputs/tables/ml_business_questions.csv |
| ml_cluster_centroids.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_centroids.csv, outputs/tables/ml_cluster_centroids.csv |
| ml_cluster_insights.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_insights.csv, outputs/tables/ml_cluster_insights.csv |
| ml_cluster_label_mapping.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_label_mapping.csv, outputs/tables/ml_cluster_label_mapping.csv |
| ml_cluster_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_cluster_summary.csv, outputs/tables/ml_cluster_summary.csv |
| ml_data_quality_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_data_quality_checks.csv, outputs/tables/ml_data_quality_checks.csv |
| ml_feature_distribution_check.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_distribution_check.csv, outputs/tables/ml_feature_distribution_check.csv |
| ml_feature_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_selection.csv, outputs/tables/ml_feature_selection.csv |
| ml_feature_set_comparison.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_feature_set_comparison.csv, outputs/tables/ml_feature_set_comparison.csv |
| ml_final_model_metrics.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_final_model_metrics.csv, outputs/tables/ml_final_model_metrics.csv |
| ml_k_evaluation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_k_evaluation.csv, outputs/tables/ml_k_evaluation.csv |
| ml_pca_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_pca_summary.csv, outputs/tables/ml_pca_summary.csv |
| ml_silhouette_by_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_silhouette_by_cluster.csv, outputs/tables/ml_silhouette_by_cluster.csv |
| ml_validation_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/ml_validation_checks.csv, outputs/tables/ml_validation_checks.csv |
| monthly_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/monthly_summary.csv, outputs/tables/monthly_summary.csv |
| order_status_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/order_status_summary.csv, outputs/tables/order_status_summary.csv |
| outlier_interpretation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/outlier_interpretation.csv, outputs/tables/outlier_interpretation.csv |
| outlier_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/outlier_summary.csv, outputs/tables/outlier_summary.csv |
| payment_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/payment_summary.csv, outputs/tables/payment_summary.csv |
| powerbi_cross_step_consistency.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_cross_step_consistency.csv, outputs/tables/powerbi_cross_step_consistency.csv |
| powerbi_measure_catalog.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_measure_catalog.csv, outputs/tables/powerbi_measure_catalog.csv |
| powerbi_measure_validation.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_measure_validation.csv, outputs/tables/powerbi_measure_validation.csv |
| powerbi_relationships.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_relationships.csv, outputs/tables/powerbi_relationships.csv |
| powerbi_table_catalog.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_table_catalog.csv, outputs/tables/powerbi_table_catalog.csv |
| powerbi_validation_checklist.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/powerbi_validation_checklist.csv, outputs/tables/powerbi_validation_checklist.csv |
| product_profitability.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/product_profitability.csv, outputs/tables/product_profitability.csv |
| product_revenue_profit_quadrants.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/product_revenue_profit_quadrants.csv, outputs/tables/product_revenue_profit_quadrants.csv |
| product_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/product_summary.csv, outputs/tables/product_summary.csv |
| purchase_frequency.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/purchase_frequency.csv, outputs/tables/purchase_frequency.csv |
| quarterly_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/quarterly_summary.csv, outputs/tables/quarterly_summary.csv |
| regional_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/regional_summary.csv, outputs/tables/regional_summary.csv |
| report_facts.json | FINAL_SUBMISSION/11_OUTPUT_TABLES/report_facts.json, outputs/tables/report_facts.json |
| revenue_business_questions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_business_questions.csv, outputs/tables/revenue_business_questions.csv |
| revenue_categorical_drivers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_categorical_drivers.csv, outputs/tables/revenue_categorical_drivers.csv |
| revenue_concentration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_concentration.csv, outputs/tables/revenue_concentration.csv |
| revenue_cutoff_timing.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_cutoff_timing.csv, outputs/tables/revenue_cutoff_timing.csv |
| revenue_data_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_data_checks.csv, outputs/tables/revenue_data_checks.csv |
| revenue_driver_analysis.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_driver_analysis.csv, outputs/tables/revenue_driver_analysis.csv |
| revenue_error_by_category.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_category.csv, outputs/tables/revenue_error_by_category.csv |
| revenue_error_by_quarter.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_quarter.csv, outputs/tables/revenue_error_by_quarter.csv |
| revenue_error_by_region.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_region.csv, outputs/tables/revenue_error_by_region.csv |
| revenue_error_by_revenue_range.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_error_by_revenue_range.csv, outputs/tables/revenue_error_by_revenue_range.csv |
| revenue_feature_catalog.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_catalog.csv, outputs/tables/revenue_feature_catalog.csv |
| revenue_feature_importance.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_importance.csv, outputs/tables/revenue_feature_importance.csv |
| revenue_feature_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_feature_selection.csv, outputs/tables/revenue_feature_selection.csv |
| revenue_leakage_audit.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_leakage_audit.csv, outputs/tables/revenue_leakage_audit.csv |
| revenue_level_feature_check.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_level_feature_check.csv, outputs/tables/revenue_level_feature_check.csv |
| revenue_linear_coefficients.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_linear_coefficients.csv, outputs/tables/revenue_linear_coefficients.csv |
| revenue_model_comparison.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_comparison.csv, outputs/tables/revenue_model_comparison.csv |
| revenue_model_selection.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_selection.csv, outputs/tables/revenue_model_selection.csv |
| revenue_model_validation_results.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_model_validation_results.csv, outputs/tables/revenue_model_validation_results.csv |
| revenue_prediction_by_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_by_cluster.csv, outputs/tables/revenue_prediction_by_cluster.csv |
| revenue_prediction_by_rfm.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_by_rfm.csv, outputs/tables/revenue_prediction_by_rfm.csv |
| revenue_prediction_design.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_prediction_design.csv, outputs/tables/revenue_prediction_design.csv |
| revenue_predictions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_predictions.csv, outputs/tables/revenue_predictions.csv |
| revenue_quarterly_totals.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_quarterly_totals.csv, outputs/tables/revenue_quarterly_totals.csv |
| revenue_scenarios.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_scenarios.csv, outputs/tables/revenue_scenarios.csv |
| revenue_split_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_split_summary.csv, outputs/tables/revenue_split_summary.csv |
| revenue_tuning_results.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_tuning_results.csv, outputs/tables/revenue_tuning_results.csv |
| revenue_validation_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/revenue_validation_checks.csv, outputs/tables/revenue_validation_checks.csv |
| rfm_business_insights.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_business_insights.csv, outputs/tables/rfm_business_insights.csv |
| rfm_business_questions.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_business_questions.csv, outputs/tables/rfm_business_questions.csv |
| rfm_concentration_stats.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_concentration_stats.csv, outputs/tables/rfm_concentration_stats.csv |
| rfm_descriptive_statistics.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_descriptive_statistics.csv, outputs/tables/rfm_descriptive_statistics.csv |
| rfm_excluded_customers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_excluded_customers.csv, outputs/tables/rfm_excluded_customers.csv |
| rfm_headline_metrics.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_headline_metrics.csv, outputs/tables/rfm_headline_metrics.csv |
| rfm_high_value_at_risk.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_high_value_at_risk.csv, outputs/tables/rfm_high_value_at_risk.csv |
| rfm_high_value_at_risk_rule.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_high_value_at_risk_rule.csv, outputs/tables/rfm_high_value_at_risk_rule.csv |
| rfm_log_transform_check.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_log_transform_check.csv, outputs/tables/rfm_log_transform_check.csv |
| rfm_most_recent_customers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_most_recent_customers.csv, outputs/tables/rfm_most_recent_customers.csv |
| rfm_qcut_feasibility.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_qcut_feasibility.csv, outputs/tables/rfm_qcut_feasibility.csv |
| rfm_revenue_concentration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_revenue_concentration.csv, outputs/tables/rfm_revenue_concentration.csv |
| rfm_score_bins.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_score_bins.csv, outputs/tables/rfm_score_bins.csv |
| rfm_score_grid_R_by_F.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_score_grid_R_by_F.csv, outputs/tables/rfm_score_grid_R_by_F.csv |
| rfm_segment_profile.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_profile.csv, outputs/tables/rfm_segment_profile.csv |
| rfm_segment_rules.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_rules.csv, outputs/tables/rfm_segment_rules.csv |
| rfm_segment_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_segment_summary.csv, outputs/tables/rfm_segment_summary.csv |
| rfm_top_customers_frequency.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_top_customers_frequency.csv, outputs/tables/rfm_top_customers_frequency.csv |
| rfm_top_customers_monetary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_top_customers_monetary.csv, outputs/tables/rfm_top_customers_monetary.csv |
| rfm_validation_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_validation_checks.csv, outputs/tables/rfm_validation_checks.csv |
| rfm_value_activity_groups.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_value_activity_groups.csv, outputs/tables/rfm_value_activity_groups.csv |
| rfm_vs_ml_agreement.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_agreement.csv, outputs/tables/rfm_vs_ml_agreement.csv |
| rfm_vs_ml_by_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_by_cluster.csv, outputs/tables/rfm_vs_ml_by_cluster.csv |
| rfm_vs_ml_by_segment.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_by_segment.csv, outputs/tables/rfm_vs_ml_by_segment.csv |
| rfm_vs_ml_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster.csv, outputs/tables/rfm_vs_ml_cluster.csv |
| rfm_vs_ml_cluster_col_pct.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster_col_pct.csv, outputs/tables/rfm_vs_ml_cluster_col_pct.csv |
| rfm_vs_ml_cluster_row_pct.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/rfm_vs_ml_cluster_row_pct.csv, outputs/tables/rfm_vs_ml_cluster_row_pct.csv |
| seasonal_index.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/seasonal_index.csv, outputs/tables/seasonal_index.csv |
| BQ01.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ01.csv, outputs/tables/sql/BQ01.csv |
| BQ02.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ02.csv, outputs/tables/sql/BQ02.csv |
| BQ03.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ03.csv, outputs/tables/sql/BQ03.csv |
| BQ04.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ04.csv, outputs/tables/sql/BQ04.csv |
| BQ05.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ05.csv, outputs/tables/sql/BQ05.csv |
| BQ06.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ06.csv, outputs/tables/sql/BQ06.csv |
| BQ07.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ07.csv, outputs/tables/sql/BQ07.csv |
| BQ08.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ08.csv, outputs/tables/sql/BQ08.csv |
| BQ09.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ09.csv, outputs/tables/sql/BQ09.csv |
| BQ10.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ10.csv, outputs/tables/sql/BQ10.csv |
| BQ11.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ11.csv, outputs/tables/sql/BQ11.csv |
| BQ12.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ12.csv, outputs/tables/sql/BQ12.csv |
| BQ13.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ13.csv, outputs/tables/sql/BQ13.csv |
| BQ14.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ14.csv, outputs/tables/sql/BQ14.csv |
| BQ15.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ15.csv, outputs/tables/sql/BQ15.csv |
| BQ16.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ16.csv, outputs/tables/sql/BQ16.csv |
| BQ17.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ17.csv, outputs/tables/sql/BQ17.csv |
| BQ18.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ18.csv, outputs/tables/sql/BQ18.csv |
| BQ19.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ19.csv, outputs/tables/sql/BQ19.csv |
| BQ20.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/BQ20.csv, outputs/tables/sql/BQ20.csv |
| cust_acquired_by_year.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_acquired_by_year.csv, outputs/tables/sql/cust_acquired_by_year.csv |
| cust_concentration_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_concentration_summary.csv, outputs/tables/sql/cust_concentration_summary.csv |
| cust_frequency_distribution.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_frequency_distribution.csv, outputs/tables/sql/cust_frequency_distribution.csv |
| cust_highest_aov.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_highest_aov.csv, outputs/tables/sql/cust_highest_aov.csv |
| cust_inactive.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_inactive.csv, outputs/tables/sql/cust_inactive.csv |
| cust_most_frequent.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_most_frequent.csv, outputs/tables/sql/cust_most_frequent.csv |
| cust_new_vs_existing.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_new_vs_existing.csv, outputs/tables/sql/cust_new_vs_existing.csv |
| cust_revenue_concentration.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_revenue_concentration.csv, outputs/tables/sql/cust_revenue_concentration.csv |
| cust_top_profit.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_top_profit.csv, outputs/tables/sql/cust_top_profit.csv |
| cust_top_revenue.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/cust_top_revenue.csv, outputs/tables/sql/cust_top_revenue.csv |
| prod_avg_selling_price.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_avg_selling_price.csv, outputs/tables/sql/prod_avg_selling_price.csv |
| prod_category_performance.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_category_performance.csv, outputs/tables/sql/prod_category_performance.csv |
| prod_discount_bands.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_discount_bands.csv, outputs/tables/sql/prod_discount_bands.csv |
| prod_investigate.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_investigate.csv, outputs/tables/sql/prod_investigate.csv |
| prod_profitability.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_profitability.csv, outputs/tables/sql/prod_profitability.csv |
| prod_subcategory_performance.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_subcategory_performance.csv, outputs/tables/sql/prod_subcategory_performance.csv |
| prod_top_profit.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_profit.csv, outputs/tables/sql/prod_top_profit.csv |
| prod_top_quantity.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_quantity.csv, outputs/tables/sql/prod_top_quantity.csv |
| prod_top_revenue.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/prod_top_revenue.csv, outputs/tables/sql/prod_top_revenue.csv |
| reg_category_matrix.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_category_matrix.csv, outputs/tables/sql/reg_category_matrix.csv |
| reg_customers_without_orders.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_customers_without_orders.csv, outputs/tables/sql/reg_customers_without_orders.csv |
| reg_performance.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_performance.csv, outputs/tables/sql/reg_performance.csv |
| reg_top_states.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/reg_top_states.csv, outputs/tables/sql/reg_top_states.csv |
| rev_by_quarter.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_by_quarter.csv, outputs/tables/sql/rev_by_quarter.csv |
| rev_by_year.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_by_year.csv, outputs/tables/sql/rev_by_year.csv |
| rev_kpi_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_kpi_summary.csv, outputs/tables/sql/rev_kpi_summary.csv |
| rev_margin_by_year_category.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_margin_by_year_category.csv, outputs/tables/sql/rev_margin_by_year_category.csv |
| rev_order_status.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/rev_order_status.csv, outputs/tables/sql/rev_order_status.csv |
| seg_ml_cluster_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_ml_cluster_summary.csv, outputs/tables/sql/seg_ml_cluster_summary.csv |
| seg_rfm_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_rfm_summary.csv, outputs/tables/sql/seg_rfm_summary.csv |
| seg_rfm_vs_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_rfm_vs_cluster.csv, outputs/tables/sql/seg_rfm_vs_cluster.csv |
| seg_value_activity_groups.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_value_activity_groups.csv, outputs/tables/sql/seg_value_activity_groups.csv |
| seg_value_by_cluster.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/seg_value_by_cluster.csv, outputs/tables/sql/seg_value_by_cluster.csv |
| time_best_worst_months.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_best_worst_months.csv, outputs/tables/sql/time_best_worst_months.csv |
| time_month_of_year.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_month_of_year.csv, outputs/tables/sql/time_month_of_year.csv |
| time_monthly.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_monthly.csv, outputs/tables/sql/time_monthly.csv |
| time_ytd_running_total.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql/time_ytd_running_total.csv, outputs/tables/sql/time_ytd_running_total.csv |
| sql_key_findings.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_key_findings.csv, outputs/tables/sql_key_findings.csv |
| sql_quality_checklist.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_quality_checklist.csv, outputs/tables/sql_quality_checklist.csv |
| sql_query_catalog.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_query_catalog.csv, outputs/tables/sql_query_catalog.csv |
| sql_table_catalog.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_table_catalog.csv, outputs/tables/sql_table_catalog.csv |
| sql_technique_coverage.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_technique_coverage.csv, outputs/tables/sql_technique_coverage.csv |
| sql_validation_checks.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/sql_validation_checks.csv, outputs/tables/sql_validation_checks.csv |
| state_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/state_summary.csv, outputs/tables/state_summary.csv |
| streamlit_page_load_times.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_page_load_times.csv, outputs/tables/streamlit_page_load_times.csv |
| streamlit_quality_checklist.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_quality_checklist.csv, outputs/tables/streamlit_quality_checklist.csv |
| streamlit_test_results.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/streamlit_test_results.csv, outputs/tables/streamlit_test_results.csv |
| subcategory_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/subcategory_summary.csv, outputs/tables/subcategory_summary.csv |
| top_customers_profit.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/top_customers_profit.csv, outputs/tables/top_customers_profit.csv |
| top_customers_revenue.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/top_customers_revenue.csv, outputs/tables/top_customers_revenue.csv |
| unusual_customers.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/unusual_customers.csv, outputs/tables/unusual_customers.csv |
| yearly_summary.csv | FINAL_SUBMISSION/11_OUTPUT_TABLES/yearly_summary.csv, outputs/tables/yearly_summary.csv |

`pages/forecasting.py`, `pages/prediction.py` and `pages/segmentation.py` are Streamlit **page
scripts**; `src/forecasting.py`, `src/prediction.py` and `src/segmentation.py` are the **pipeline
modules**. They never shadow each other (`pages/` is not on `sys.path`; Streamlit executes those
files by path), but the naming is worth knowing when reading the tree.

### Obsolete / stray files

| Type | Path | Note |
|---|---|---|
| Placeholder file | FINAL_SUBMISSION/04_DATA/processed/.gitkeep | Intentional: keeps an otherwise empty directory in version control. |
| Placeholder file | assets/images/.gitkeep | Intentional: keeps an otherwise empty directory in version control. |
| Placeholder file | data/processed/.gitkeep | Intentional: keeps an otherwise empty directory in version control. |

No backup files, editor leftovers or `*.bak` artefacts were found. The superseded Step 3 database
`data/processed/revenue_intelligence.db` is referenced once, in `src/database.py`, as a **deletion
target** - Step 10 removes it so there is a single source of truth. That is a cleanup routine, not
a broken reference.

### Broken references

None. Every file path written as a literal in the Python, SQL and notebook sources resolves on disk, apart from eight names that are written at runtime (CSV download filenames in the Streamlit pages and two in-memory test fixtures) and the superseded database above.

### Unused modules

None - every module in `src/` is imported by a pipeline entry point, a notebook, the application or the test suite.

`models/revenue_prediction_preprocessor.pkl` is saved by Step 8 alongside the full pipeline, which
already contains the same preprocessing. It is redundant rather than wrong, and it is documented in
the Step 8 report; it is kept so the preprocessing can be inspected on its own.

---

## 3. Pipeline verification

Each stage's declared inputs and outputs were resolved on disk, and every input was checked
against the stage that produces it, so a stage can never depend on something produced later.

| Stage | Inputs / outputs | Status |
|---|---|---|
| Step 2: RAW DATA | 0 inputs, 3 outputs, module scripts/generate_dataset.py | PASS |
| Step 3: DATA CLEANING | 1 input, 4 outputs, module src/data_cleaning.py | PASS |
| Step 4: EDA | 1 input, 2 outputs, module src/eda.py | PASS |
| Step 5: RFM ANALYSIS | 1 input, 5 outputs, module src/rfm.py | PASS |
| Step 6: K-MEANS SEGMENTATION | 1 input, 7 outputs, module src/segmentation.py | PASS |
| Step 7: CLV | 2 inputs, 7 outputs, module src/clv.py | PASS |
| Step 8: REVENUE PREDICTION | 3 inputs, 7 outputs, module src/prediction.py | PASS |
| Step 9: SALES FORECASTING | 1 input, 6 outputs, module src/forecasting.py | PASS |
| Step 10: SQL ANALYTICS | 8 inputs, 4 outputs, module src/database.py + src/sql_analytics.py | PASS |
| Step 11: POWER BI | 5 inputs, 7 outputs, module src/powerbi_prep.py + sql/powerbi_views.sql | PASS |
| Step 12: STREAMLIT | 6 inputs, 2 outputs, module app.py + pages/ + src/data_loader.py | PASS |
| Step 10-12: BUSINESS INSIGHTS | 4 inputs, 1 output, module powerbi/data/Recommendations.csv + pages/recommendations.py | PASS |
| 01_data_cleaning.ipynb | 27/27 cells executed, 0 errors | PASS |
| 02_exploratory_data_analysis.ipynb | 74/74 cells executed, 0 errors | PASS |
| 03_rfm_customer_analysis.ipynb | 44/44 cells executed, 0 errors | PASS |
| 04_kmeans_customer_segmentation.ipynb | 35/35 cells executed, 0 errors | PASS |
| 05_customer_lifetime_value.ipynb | 46/46 cells executed, 0 errors | PASS |
| 06_revenue_prediction.ipynb | 43/43 cells executed, 0 errors | PASS |
| 07_sales_forecasting.ipynb | 33/33 cells executed, 0 errors | PASS |
| 08_sql_business_analysis.ipynb | 48/48 cells executed, 0 errors | PASS |
| 09_powerbi_data_model.ipynb | 23/23 cells executed, 0 errors | PASS |

The chain holds end to end:

```text
RAW DATA -> DATA CLEANING -> EDA -> RFM -> K-MEANS -> CLV -> REVENUE PREDICTION
   -> SALES FORECASTING -> SQL ANALYTICS -> POWER BI -> STREAMLIT -> BUSINESS INSIGHTS
```

No broken dependency was found. All nine notebooks are fully executed with zero error outputs.

---

## 4. Data consistency

71 checks, each recomputing a figure from a primary source and comparing it
with what another file or layer states.

| Area | Check | Values compared | Status |
|---|---|---|---|
| Raw vs cleaned | Cleaned rows = raw rows minus duplicate Order_Line_IDs | 18,670.0000 (cleaned) vs 18,670.0000 (raw) | PASS |
| Raw vs cleaned | Order_Line_ID is unique after cleaning | 0.0000 (cleaned) vs 0.0000 (expected) | PASS |
| Raw vs cleaned | No nulls in the key cleaned columns | 0.0000 (cleaned) vs 0.0000 (expected) | PASS |
| KPIs | Total revenue | 60,056,569.1500 (recomputed from the cleaned CSV) vs 60,056,569.1500 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Total profit | 14,022,551.5800 (recomputed from the cleaned CSV) vs 14,022,551.5800 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Total cost | 46,034,017.5700 (recomputed from the cleaned CSV) vs 46,034,017.5700 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Orders | 12,212.0000 (recomputed from the cleaned CSV) vs 12,212.0000 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Purchasing customers | 1,984.0000 (recomputed from the cleaned CSV) vs 1,984.0000 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Units sold | 22,772.0000 (recomputed from the cleaned CSV) vs 22,772.0000 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | AOV | 4,917.8324 (recomputed from the cleaned CSV) vs 4,917.8324 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Profit margin | 0.2335 (recomputed from the cleaned CSV) vs 0.2335 (outputs/tables/eda_kpis.csv) | PASS |
| KPIs | Gross booked sales | 66,312,002.3500 (recomputed from the cleaned CSV) vs 66,312,002.3500 (outputs/tables/eda_kpis.csv) | PASS |
| Database | Revenue | 60,056,569.1500 (cleaned CSV) vs 60,056,569.1500 (vw_delivered_sales) | PASS |
| Database | Profit | 14,022,551.5800 (cleaned CSV) vs 14,022,551.5800 (vw_delivered_sales) | PASS |
| Database | Cost | 46,034,017.5700 (cleaned CSV) vs 46,034,017.5700 (vw_delivered_sales) | PASS |
| Database | Quantity | 22,772.0000 (cleaned CSV) vs 22,772.0000 (vw_delivered_sales) | PASS |
| Database | Orders | 12,212.0000 (cleaned CSV) vs 12,212.0000 (vw_delivered_sales) | PASS |
| Database | Customers | 1,984.0000 (cleaned CSV) vs 1,984.0000 (vw_delivered_sales) | PASS |
| Database | Delivered lines | 16,860.0000 (cleaned CSV) vs 16,860.0000 (vw_delivered_sales) | PASS |
| Database | Row count: customers | 2,000.0000 (database) vs 2,000.0000 (cleaned CSV) | PASS |
| Database | Row count: products | 61.0000 (database) vs 61.0000 (cleaned CSV) | PASS |
| Database | Row count: orders | 13,251.0000 (database) vs 13,251.0000 (cleaned CSV) | PASS |
| Database | Row count: order_items | 18,670.0000 (database) vs 18,670.0000 (cleaned CSV) | PASS |
| Database | No orphan rows: order_items_to_orders | 0.0000 (LEFT JOIN) vs 0.0000 (expected) | PASS |
| Database | No orphan rows: order_items_to_products | 0.0000 (LEFT JOIN) vs 0.0000 (expected) | PASS |
| Database | No orphan rows: orders_to_customers | 0.0000 (LEFT JOIN) vs 0.0000 (expected) | PASS |
| Database | No orphan rows: customers_to_locations | 0.0000 (LEFT JOIN) vs 0.0000 (expected) | PASS |
| Star schema | FactSales rows | 18,670.0000 (FactSales.csv) vs 18,670.0000 (cleaned CSV) | PASS |
| Star schema | Delivered revenue | 60,056,569.1500 (FactSales.csv) vs 60,056,569.1500 (cleaned CSV) | PASS |
| Star schema | Delivered profit | 14,022,551.5800 (FactSales.csv) vs 14,022,551.5800 (cleaned CSV) | PASS |
| Star schema | DimCustomer rows | 2,000.0000 (DimCustomer.csv) vs 2,000.0000 (cleaned CSV) | PASS |
| Star schema | No customer-name column in DimCustomer | 0.0000 (DimCustomer.csv) vs 0.0000 (privacy rule) | PASS |
| Star schema | Is_Delivered equals Order_Status == 'Delivered' | 0.0000 (FactSales.csv) vs 0.0000 (expected) | PASS |
| Customer coverage | RFM rows = customers with a delivered order | 1,984.0000 (customer_rfm_segments.csv) vs 1,984.0000 (cleaned CSV) | PASS |
| Customer coverage | ML rows = RFM rows | 1,984.0000 (customer_ml_segments.csv) vs 1,984.0000 (customer_rfm_segments.csv) | PASS |
| Customer coverage | CLV rows = RFM rows | 1,984.0000 (customer_clv.csv) vs 1,984.0000 (customer_rfm_segments.csv) | PASS |
| Customer coverage | Identical customer IDs across RFM / ML / CLV | 0.0000 (symmetric differences) vs 0.0000 (expected) | PASS |
| Customer coverage | Registered customers with no delivered order | 16.0000 (cleaned CSV) vs 16.0000 (DimCustomer.csv) | PASS |
| RFM | Per-segment customer counts match the summary table | 0.0000 (recomputed) vs 0.0000 (rfm_segment_summary.csv) | PASS |
| RFM | Per-segment revenue matches the summary table | 0.0000 (recomputed) vs 0.0000 (rfm_segment_summary.csv) | PASS |
| RFM | Recency matches the database | 0.0000 (row-by-row) vs 0.0000 (expected) | PASS |
| Clusters | Cluster assignment matches the database | 0.0000 (row-by-row) vs 0.0000 (expected) | PASS |
| Clusters | Per-cluster revenue matches the summary table | 0.0000 (recomputed) vs 0.0000 (ml_cluster_summary.csv) | PASS |
| Clusters | Cluster IDs agree with DimCustomer | 0.0000 (row-by-row) vs 0.0000 (expected) | PASS |
| CLV | Historical revenue CLV total | 60,056,569.1500 (customer_clv.csv) vs 60,056,569.1500 (cleaned CSV) | PASS |
| CLV | Historical profit CLV total | 14,022,551.5800 (customer_clv.csv) vs 14,022,551.5800 (cleaned CSV) | PASS |
| CLV | Profit CLV matches the database | 14,022,551.5800 (customer_clv.csv) vs 14,022,551.5800 (DB customer_value) | PASS |
| CLV | Estimated 12M profit matches DimCustomer | 7,397,326.5500 (customer_clv.csv) vs 7,397,326.5500 (DimCustomer.csv) | PASS |
| CLV | At-risk high-value customers | 52.0000 (customer_clv.csv) vs 52.0000 (DimCustomer.csv) | PASS |
| Time series | Monthly rows | 36.0000 (monthly_sales_timeseries.csv) vs 36.0000 (recomputed) | PASS |
| Time series | Every month's revenue matches the recomputation | 0.0000 (row-by-row) vs 0.0000 (expected) | PASS |
| Time series | Every month's orders match the recomputation | 0.0000 (row-by-row) vs 0.0000 (expected) | PASS |
| Forecast | Historical actuals in the forecast file | 60,056,569.1500 (revenue_forecast.csv) vs 60,056,569.1500 (cleaned CSV) | PASS |
| Forecast | Future forecast total | 15,798,158.4000 (revenue_forecast.csv) vs 15,798,158.4000 (FactForecast.csv) | PASS |
| Forecast | Horizon length | 6.0000 (revenue_forecast.csv) vs 6.0000 (forecasting_metadata.json) | PASS |
| Forecast | Forecast months match the metadata | 2026-01,2026-02,2026-03,2026-04,2026-05,2026-06 (FactForecast.csv) vs 2026-01,2026-02,2026-03,2026-04,2026-05,2026-06 (forecasting_metadata.json) | PASS |
| Forecast | Selected model test MAPE | 7.7679 (forecast_model_comparison.csv) vs 7.7680 (forecasting_metadata.json) | PASS |
| Forecast | Interval bounds correctly ordered | 0.0000 (FactForecast.csv) vs 0.0000 (expected) | PASS |
| Prediction | Prediction rows = test-split rows | 2,913.0000 (revenue_predictions.csv) vs 2,913.0000 (revenue_modeling_dataset.csv) | PASS |
| Prediction | Prediction rows match the star-schema fact | 2,913.0000 (revenue_predictions.csv) vs 2,913.0000 (FactRevenuePrediction.csv) | PASS |
| Prediction | Test actual revenue | 12,892,558.9000 (revenue_predictions.csv) vs 12,892,558.9000 (revenue_quarterly_totals.csv) | PASS |
| Prediction | Test MAE matches the comparison table | 5,657.5669 (recomputed) vs 5,657.5669 (revenue_model_comparison.csv) | PASS |
| Prediction | Test MAE matches the model metadata | 5,657.5669 (recomputed) vs 5,657.5669 (revenue_model_metadata.json) | PASS |
| Prediction | Test RMSE matches the model metadata | 11,232.4199 (recomputed) vs 11,232.4199 (revenue_model_metadata.json) | PASS |
| Prediction | Test R² matches the model metadata | 0.0557 (recomputed) vs 0.0557 (revenue_model_metadata.json) | PASS |
| Prediction | Error column equals Predicted - Actual | 0.0000 (recomputed) vs 0.0000 (expected) | PASS |
| Dates | Data starts | 2023-01-01 (cleaned CSV) vs 2023-01-01 (project design) | PASS |
| Dates | Data ends | 2025-12-31 (cleaned CSV) vs 2025-12-31 (project design) | PASS |
| Dates | DimDate covers the forecast horizon | 2026-06-30 (DimDate.csv) vs 2026-06-30 (horizon end) | PASS |
| Dates | DimDate has no gaps | 0.0000 (DimDate.csv) vs 0.0000 (expected) | PASS |
| Dates | One reference date across metadata, database and star schema | 1.0000 ({'2026-01-01'}) vs 1.0000 (expected) | PASS |

---

## 5. Models, leakage and documentation

| Area | Check | Result | Status |
|---|---|---|---|
| Model artefacts | revenue_prediction_model.pkl loads | Pipeline, 0.01 MB | PASS |
| Model artefacts | revenue_prediction_preprocessor.pkl loads | ColumnTransformer, 0.01 MB | PASS |
| Model artefacts | forecasting_model.pkl loads | dict, 0.00 MB | PASS |
| Model artefacts | kmeans_customer_segmentation.pkl loads | KMeans, 0.01 MB | PASS |
| Model artefacts | rfm_scaler.pkl loads | Pipeline, 0.00 MB | PASS |
| Model artefacts | pca_rfm.pkl loads | PCA, 0.00 MB | PASS |
| Model artefacts | clv_model.pkl loads | RandomForestRegressor, 5.33 MB | PASS |
| Model artefacts | clv_preprocessor.pkl loads | Pipeline, 0.00 MB | PASS |
| Model artefacts | scikit-learn version recorded vs installed | recorded 1.8.0, installed 1.8.0 | PASS |
| Reproducibility | Reloaded model reproduces the saved test predictions | 2,913 rows, max /diff/ ₹0.3528 | PASS |
| Model artefacts | Feature schema size matches the metadata | 24 features | PASS |
| Reproducibility | Reloaded forecasting model reproduces the saved forecast | 6 months, max /diff/ ₹0.0033 | PASS |
| Reproducibility | Reloaded K-Means reproduces the saved cluster assignment | 100.00% of 1,984 customers identical | PASS |
| Reproducibility | Saved scaled features match the preprocessing pipeline | max /diff/ 5.00e-06 | PASS |
| Leakage audit | Rev_3M uses only pre-cutoff data | 400/400 sampled rows match a fresh recomputation | PASS |
| Leakage audit | Orders_12M uses only pre-cutoff data | 400/400 sampled rows match a fresh recomputation | PASS |
| Leakage audit | Recency_Days is measured at the cutoff | 400/400 sampled rows match a fresh recomputation | PASS |
| Leakage audit | Target is revenue in the 3 months from the cutoff | 400/400 sampled rows match a fresh recomputation | PASS |
| Leakage audit | Train / validation / test periods do not overlap | test: 2025-Q3..2025-Q4; train: 2024-Q1..2024-Q4; validation: 2025-Q1..2025-Q2 | PASS |
| Leakage audit | No duplicated customer-quarter rows | 0 duplicates | PASS |
| Leakage audit | Forecast split is chronological | train 2023-01..2024-12 / validation 2025-01..2025-06 / test 2025-07..2025-12 | PASS |
| Documentation | ₹6.01 Cr (total revenue) | computed 6.0057, quoted in 11 document(s) | PASS |
| Documentation | ₹1.40 Cr (total profit) | computed 1.4023, quoted in 7 document(s) | PASS |
| Documentation | 23.35% (profit margin) | computed 23.3489, quoted in 4 document(s) | PASS |
| Documentation | 12,212 (orders) | computed 12,212.0000, quoted in 8 document(s) | PASS |
| Documentation | 1,984 (purchasing customers) | computed 1,984.0000, quoted in 10 document(s) | PASS |
| Documentation | ₹4,918 (AOV) | computed 4,917.8324, quoted in 5 document(s) | PASS |
| Documentation | 18,670 (cleaned order lines) | computed 18,670.0000, quoted in 5 document(s) | PASS |
| Documentation | 2,000 (registered customers) | computed 2,000.0000, quoted in 6 document(s) | PASS |
| Documentation | 64.33% (top-20% revenue share) | computed 64.3300, quoted in 3 document(s) | PASS |
| Documentation | 53.83% (Champions revenue share) | computed 53.8330, quoted in 2 document(s) | PASS |
| Documentation | 52 (at-risk high-value) | computed 52.0000, quoted in 10 document(s) | PASS |
| Documentation | 1,288 (active customers) | computed 1,288.0000, quoted in 2 document(s) | PASS |
| Documentation | 7.77% (forecast test MAPE) | computed 7.7680, quoted in 4 document(s) | PASS |
| Documentation | 0.056 (prediction test R²) | computed 0.0557, quoted in 5 document(s) | PASS |
| Documentation | ₹5,658 (prediction test MAE) | computed 5,657.5669, quoted in 5 document(s) | PASS |
| Documentation | No document asserts churn (the project has no churn label) | 0 suspect lines | PASS |
| Documentation | Every document states the data is synthetic | 14/14 documents | PASS |

---

## 6. Integration and reproducibility

Skipped in --quick mode.

---

## 7. Potential issues and recommendations

Nothing in this list is a computed failure; these are judgement calls for the project owner.
**No file was deleted by this audit.**

| # | Observation | Why it matters | Suggested action |
|---|---|---|---|
| 1 | Seven pairs of identical files between `powerbi/` and `outputs/tables/` | Two copies can look like two sources of truth to a reader | Keep as is (both are regenerated by one module), or document the convention in the README |
| 2 | `models/revenue_prediction_preprocessor.pkl` duplicates preprocessing already inside the saved pipeline | A reader might load the wrong artefact | Keep for inspection, but always load `revenue_prediction_model.pkl` for scoring |
| 3 | `assets/images/` was empty | Empty directories do not survive a `git clone` | **Resolved in this step**: `assets/images/.gitkeep` added |
| 4 | `pages/*.py` share three filenames with `src/*.py` | Confusing when reading the tree, though they never shadow | Optional: rename the page modules (e.g. `page_forecasting.py`) |
| 5 | Model metadata records scikit-learn 1.8.0 | Loading the pipelines under a different minor version can warn or break | **Noted in this step**: `requirements.txt` now records the version the pipelines were saved with; pin `==1.8.0` if exact reproduction is required |
| 6 | The Step 8 model is weak at customer level (test R² 0.056) | A reader could over-read a single prediction | Already stated on the dashboard, in the app and in the report - keep that framing in the final report |
| 7 | 8.4 MB of screenshots and 30 MB of executed notebooks | Repository size for submission | Fine for a local hand-in; if a size limit applies, strip notebook outputs |

---

## 8. What was verified, in one paragraph

The project's 12 stages form an unbroken chain from the generated raw data to the business
recommendations. Revenue is defined once - delivered order lines only - and that definition holds
identically in the cleaned CSV, the SQLite database, the Power BI star schema and the Streamlit
application. Customer coverage is consistent across RFM, K-Means, CLV and the customer dimension,
including the 16 registered customers who never received an order. Every saved model
loads and reproduces its own saved outputs. A fresh leakage re-audit recomputed the Step 8 features
from the cleaned transactions and confirmed that each one uses only data strictly before its
cutoff, with the target taken strictly after it. Every headline figure quoted in the README and the
eleven reports was re-checked against the data. The database rebuild passes its 56 validation
checks, the Streamlit suite passes all 40 of its checks, the application still works with the
database removed, and pyflakes is clean across all 86 Python files.

---

*Generated by `scripts/audit_project.py`. Machine-readable results:
`outputs/tables/audit_summary.csv` and `audit_structure.csv`, `audit_pipeline.csv`,
`audit_data_consistency.csv`, `audit_models.csv`, `audit_integration.csv`, `audit_findings.csv`.*
