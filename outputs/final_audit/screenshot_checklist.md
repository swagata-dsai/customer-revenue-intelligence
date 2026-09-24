# Screenshot Checklist

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

**81 images are already in `outputs/screenshots/`.**
They were assembled by copying figures the pipeline produced and by rendering
two dataset previews directly from the real CSV files. **No image was
fabricated.**

Three things to understand about the pack before you use it:

1. The twelve `*_streamlit_*.png` files are **real screenshots** of the running
   application.
2. The ten `*_MOCKUP.png` files are **design mockups rendered from the real
   data**, not Power BI Desktop screenshots. The suffix is in the filename on
   purpose — keep it there.
3. Everything else is a chart the analysis produced.

## A. Data — dataset previews

| File | Shows | Status |
|---|---|---|
| `01_raw_dataset_preview.png` | Rendered from the actual CSV by `scripts/build_demo.py` | ✔ in pack |
| `02_clean_dataset_preview.png` | Rendered from the actual CSV by `scripts/build_demo.py` | ✔ in pack |

### A. Data

| File | Shows | Source | Status |
|---|---|---|---|
| `03_data_quality_missing_before.png` | Missing values by column in the raw extract | `outputs/figures/data_quality/01_missing_values_before.png` | ✔ in pack |
| `04_data_quality_missing_after.png` | Missing values after cleaning — all zero | `outputs/figures/data_quality/02_missing_values_after.png` | ✔ in pack |
| `05_data_quality_issue_summary.png` | Data-quality issue classes by records affected | `outputs/figures/data_quality/04_data_quality_issue_summary.png` | ✔ in pack |
| `06_outlier_distribution.png` | Values flagged by the 1.5×IQR rule (flagged, not removed) | `outputs/figures/data_quality/03_outlier_distribution.png` | ✔ in pack |

### B. EDA

| File | Shows | Source | Status |
|---|---|---|---|
| `07_revenue_trend_monthly.png` | Monthly delivered revenue across 36 months | `outputs/figures/monthly_revenue_trend.png` | ✔ in pack |
| `08_profit_trend_monthly.png` | Monthly delivered profit and margin | `outputs/figures/monthly_profit_trend.png` | ✔ in pack |
| `09_revenue_growth_mom.png` | Month-over-month revenue growth | `outputs/figures/mom_revenue_growth.png` | ✔ in pack |
| `10_customer_concentration.png` | Cumulative revenue against cumulative customers | `outputs/figures/revenue_concentration_curve.png` | ✔ in pack |
| `11_customer_revenue_distribution.png` | Distribution of revenue per customer | `outputs/figures/customer_revenue_distribution.png` | ✔ in pack |
| `12_purchase_frequency.png` | Purchase frequency across the customer base | `outputs/figures/purchase_frequency.png` | ✔ in pack |
| `13_category_revenue_vs_profit.png` | Revenue against profit by category | `outputs/figures/category_revenue_vs_profit.png` | ✔ in pack |
| `14_product_quadrant.png` | Revenue–profit quadrant for all products | `outputs/figures/product_revenue_profit_quadrant.png` | ✔ in pack |
| `15_regional_revenue.png` | Revenue and profit by region | `outputs/figures/regional_revenue.png` | ✔ in pack |
| `16_correlation_heatmap.png` | Correlation matrix of the numeric measures | `outputs/figures/correlation_heatmap.png` | ✔ in pack |
| `17_discount_margin.png` | Discount band against profit margin | `outputs/figures/discount_profit_relationship.png` | ✔ in pack |
| `18_order_status_value.png` | Order value by delivered / returned / cancelled | `outputs/figures/order_status_value.png` | ✔ in pack |

### C. RFM

| File | Shows | Source | Status |
|---|---|---|---|
| `19_rfm_recency_distribution.png` | Recency distribution across the base | `outputs/figures/rfm_recency_distribution.png` | ✔ in pack |
| `20_rfm_frequency_distribution.png` | Frequency distribution | `outputs/figures/rfm_frequency_distribution.png` | ✔ in pack |
| `21_rfm_monetary_distribution.png` | Monetary-value distribution | `outputs/figures/rfm_monetary_distribution.png` | ✔ in pack |
| `22_rfm_segment_distribution.png` | Customer count by RFM segment | `outputs/figures/rfm_segment_distribution.png` | ✔ in pack |
| `23_rfm_revenue_contribution.png` | Revenue contribution by RFM segment | `outputs/figures/rfm_revenue_contribution.png` | ✔ in pack |
| `24_rfm_segment_matrix.png` | Segment matrix over recency and combined FM score | `outputs/figures/rfm_segment_matrix.png` | ✔ in pack |

### D. K-Means

| File | Shows | Source | Status |
|---|---|---|---|
| `25_kmeans_feature_transformation.png` | Features before and after log1p → scaling | `outputs/figures/kmeans_feature_transformation.png` | ✔ in pack |
| `26_kmeans_elbow_curve.png` | Inertia against K (elbow curve) | `outputs/figures/kmeans_elbow_curve.png` | ✔ in pack |
| `27_kmeans_silhouette_scores.png` | Silhouette coefficient against K | `outputs/figures/kmeans_silhouette_scores.png` | ✔ in pack |
| `28_kmeans_silhouette_diagram.png` | Silhouette diagram for the selected model | `outputs/figures/kmeans_silhouette_diagram.png` | ✔ in pack |
| `29_kmeans_cluster_pca.png` | Clusters projected onto the first two components | `outputs/figures/cluster_pca_visualization.png` | ✔ in pack |
| `30_kmeans_cluster_profile.png` | Cluster centroid profiles on R, F and M | `outputs/figures/cluster_centroid_profile.png` | ✔ in pack |
| `31_kmeans_cluster_revenue.png` | Revenue contribution by cluster | `outputs/figures/cluster_revenue.png` | ✔ in pack |
| `32_rfm_vs_cluster_agreement.png` | RFM segments cross-tabulated against clusters | `outputs/figures/rfm_vs_ml_cluster_heatmap.png` | ✔ in pack |

### E. CLV

| File | Shows | Source | Status |
|---|---|---|---|
| `33_clv_distribution.png` | Distribution of historical customer value | `outputs/figures/clv_distribution.png` | ✔ in pack |
| `34_clv_value_concentration.png` | Concentration of customer value | `outputs/figures/clv_value_concentration.png` | ✔ in pack |
| `35_clv_model_comparison.png` | Forward-value model comparison | `outputs/figures/clv_model_comparison.png` | ✔ in pack |
| `36_clv_actual_vs_predicted.png` | Actual against estimated 12-month value | `outputs/figures/clv_actual_vs_predicted.png` | ✔ in pack |
| `37_clv_by_rfm_segment.png` | Customer value by RFM segment | `outputs/figures/clv_by_rfm_segment.png` | ✔ in pack |
| `38_clv_feature_importance.png` | Permutation importance for the value model | `outputs/figures/clv_feature_importance.png` | ✔ in pack |

### F. Prediction

| File | Shows | Source | Status |
|---|---|---|---|
| `39_prediction_actual_vs_predicted.png` | Actual against predicted next-quarter revenue | `outputs/figures/actual_vs_predicted_revenue.png` | ✔ in pack |
| `40_prediction_model_comparison.png` | Models and baselines on the test split | `outputs/figures/revenue_model_comparison.png` | ✔ in pack |
| `41_prediction_feature_importance.png` | Permutation feature importance | `outputs/figures/revenue_feature_importance.png` | ✔ in pack |
| `42_prediction_error_distribution.png` | Prediction error distribution | `outputs/figures/prediction_error_distribution.png` | ✔ in pack |
| `43_prediction_error_by_revenue_range.png` | Error by customer revenue range | `outputs/figures/prediction_error_by_revenue_range.png` | ✔ in pack |
| `44_prediction_timeline.png` | Actual against predicted by target quarter | `outputs/figures/revenue_prediction_timeline.png` | ✔ in pack |

### G. Forecasting

| File | Shows | Source | Status |
|---|---|---|---|
| `45_forecast_historical_revenue.png` | Historical monthly revenue series | `outputs/figures/forecasting/historical_revenue_trend.png` | ✔ in pack |
| `46_forecast_acf_pacf.png` | ACF and PACF of the revenue series | `outputs/figures/forecasting/acf_pacf.png` | ✔ in pack |
| `47_forecast_model_comparison.png` | Candidate forecasting models compared | `outputs/figures/forecasting/forecast_model_comparison.png` | ✔ in pack |
| `48_forecast_backtest.png` | Rolling-origin backtest results | `outputs/figures/forecasting/backtest_results.png` | ✔ in pack |
| `49_forecast_actual_vs_forecast.png` | Forecast with 80% and 95% prediction intervals | `outputs/figures/forecasting/actual_vs_forecast.png` | ✔ in pack |
| `50_forecast_seasonal_pattern.png` | Seasonal decomposition of the series | `outputs/figures/forecasting/seasonal_pattern.png` | ✔ in pack |

### H. SQL

| File | Shows | Source | Status |
|---|---|---|---|
| `51_sql_er_diagram.png` | Entity–relationship diagram of the database | `outputs/figures/sql/er_diagram.png` | ✔ in pack |
| `52_sql_top10_customers.png` | Top 10 customers by revenue (SQL result) | `outputs/figures/sql/sql_top10_customers.png` | ✔ in pack |
| `53_sql_customer_concentration.png` | Revenue concentration (SQL result) | `outputs/figures/sql/sql_customer_concentration.png` | ✔ in pack |
| `54_sql_revenue_by_rfm_segment.png` | Revenue by RFM segment (SQL result) | `outputs/figures/sql/sql_revenue_by_rfm_segment.png` | ✔ in pack |
| `55_sql_monthly_revenue_growth.png` | Monthly revenue growth (window function result) | `outputs/figures/sql/sql_monthly_revenue_growth.png` | ✔ in pack |
| `56_sql_region_category_margin.png` | Region × category margin test (SQL result) | `outputs/figures/sql/sql_region_category_margin.png` | ✔ in pack |

### I. Power BI (design mockup)

| File | Shows | Source | Status |
|---|---|---|---|
| `57_powerbi_home_MOCKUP.png` | Home / navigation page — design mockup | `outputs/figures/powerbi/mockups/00_home_mockup.png` | ✔ in pack |
| `58_powerbi_executive_overview_MOCKUP.png` | Executive Overview — design mockup | `outputs/figures/powerbi/mockups/01_executive_overview_mockup.png` | ✔ in pack |
| `59_powerbi_revenue_intelligence_MOCKUP.png` | Revenue Intelligence — design mockup | `outputs/figures/powerbi/mockups/02_revenue_intelligence_mockup.png` | ✔ in pack |
| `60_powerbi_customer_intelligence_MOCKUP.png` | Customer Intelligence — design mockup | `outputs/figures/powerbi/mockups/03_customer_intelligence_mockup.png` | ✔ in pack |
| `61_powerbi_customer_segmentation_MOCKUP.png` | Customer Segmentation — design mockup | `outputs/figures/powerbi/mockups/04_customer_segmentation_mockup.png` | ✔ in pack |
| `62_powerbi_product_analytics_MOCKUP.png` | Product Analytics — design mockup | `outputs/figures/powerbi/mockups/05_product_analytics_mockup.png` | ✔ in pack |
| `63_powerbi_regional_analytics_MOCKUP.png` | Regional Analytics — design mockup | `outputs/figures/powerbi/mockups/06_regional_analytics_mockup.png` | ✔ in pack |
| `64_powerbi_prediction_forecast_MOCKUP.png` | Prediction & Forecast — design mockup | `outputs/figures/powerbi/mockups/07_prediction_forecast_mockup.png` | ✔ in pack |
| `65_powerbi_recommendations_MOCKUP.png` | Business Recommendations — design mockup | `outputs/figures/powerbi/mockups/08_business_recommendations_mockup.png` | ✔ in pack |
| `66_powerbi_drillthrough_MOCKUP.png` | Customer-detail drill-through — design mockup | `outputs/figures/powerbi/mockups/09_customer_detail_drillthrough_mockup.png` | ✔ in pack |

### J. Streamlit (real screenshot)

| File | Shows | Source | Status |
|---|---|---|---|
| `67_streamlit_home.png` | Home | `outputs/figures/streamlit/01_home.png` | ✔ in pack |
| `68_streamlit_executive_overview.png` | Executive Overview | `outputs/figures/streamlit/02_executive_overview.png` | ✔ in pack |
| `69_streamlit_revenue_intelligence.png` | Revenue Intelligence | `outputs/figures/streamlit/03_revenue_intelligence.png` | ✔ in pack |
| `70_streamlit_customer_intelligence.png` | Customer Intelligence | `outputs/figures/streamlit/04_customer_intelligence.png` | ✔ in pack |
| `71_streamlit_customer_segmentation.png` | Customer Segmentation | `outputs/figures/streamlit/05_customer_segmentation.png` | ✔ in pack |
| `72_streamlit_product_analytics.png` | Product Analytics | `outputs/figures/streamlit/06_product_analytics.png` | ✔ in pack |
| `73_streamlit_regional_analytics.png` | Regional Analytics | `outputs/figures/streamlit/07_regional_analytics.png` | ✔ in pack |
| `74_streamlit_revenue_prediction.png` | Revenue Prediction | `outputs/figures/streamlit/08_revenue_prediction.png` | ✔ in pack |
| `75_streamlit_sales_forecast.png` | Sales Forecast | `outputs/figures/streamlit/09_sales_forecast.png` | ✔ in pack |
| `76_streamlit_recommendations.png` | Business Recommendations | `outputs/figures/streamlit/10_business_recommendations.png` | ✔ in pack |
| `77_streamlit_data_explorer.png` | Data Explorer | `outputs/figures/streamlit/11_data_explorer.png` | ✔ in pack |
| `78_streamlit_about.png` | About the Project | `outputs/figures/streamlit/12_about_project.png` | ✔ in pack |

### K. Diagrams

| File | Shows | Source | Status |
|---|---|---|---|
| `79_architecture.png` | Solution architecture | `outputs/figures/report/architecture.png` | ✔ in pack |
| `80_implementation_flowchart.png` | Implementation flowchart with the three validation gates | `outputs/figures/report/flowchart.png` | ✔ in pack |
| `81_graphical_abstract.png` | Pipeline from customer data to business decisions | `outputs/figures/report/graphical_abstract.png` | ✔ in pack |

## Sources that were missing

_None. Every listed source existed._

## Images you must still capture yourself

These cannot be produced without the live tool, so no file was invented for
them. Capture them only if you want them; the demo works without.

| Wanted | How to capture | Needed for |
|---|---|---|
| SQL query running in a terminal | Run `sqlite3 data/customer_revenue_intelligence.db`, paste the reconciliation query from `outputs/viva/sql_demo_script.md`, screenshot the terminal showing the query **and** its output | Optional — the SQL result charts (`52`–`56`) already carry the findings |
| Power BI Desktop report pages | Only possible on Windows. Open Power BI Desktop, build the model from `powerbi/POWERBI_BUILD_GUIDE.md`, then screenshot each page | Only if you complete the `.pbix`. Until then the mockups are the honest artefact |
| Jupyter notebook with live output | Open any notebook in `notebooks/`, run a cell, screenshot | Optional — the notebooks are committed with outputs already saved |
| The application running on your machine | `streamlit run app.py`, then screenshot each page | Optional — twelve real screenshots are already in the pack |

## Where each image is used

| Destination | Which images |
|---|---|
| **Report** (already embedded) | 9 figures are already in the built report — you do not need to add any |
| **PPT** (already embedded) | 9 images already in the deck, including one real Streamlit screenshot and one labelled mockup |
| **GitHub README** | `79_architecture.png`, `67_streamlit_home.png`, `68_streamlit_executive_overview.png`, `58_powerbi_executive_overview_MOCKUP.png` |
| **Viva / demo fallback** | The whole folder — if the live app fails, open `outputs/screenshots/` and walk the numbered sequence |

## Naming convention

`NN_area_subject[_MOCKUP].png`

- `NN` — two-digit sequence in demonstration order, so sorting the folder gives
  you the demo running order.
- `area` — `data`, `revenue`, `rfm`, `kmeans`, `clv`, `prediction`, `forecast`,
  `sql`, `powerbi`, `streamlit`, or a diagram name.
- `_MOCKUP` — mandatory suffix on any image that is a design mockup rather than
  a screenshot of a running tool. Do not remove it.

## Regenerating the pack

```bash
python scripts/build_demo.py
```

This rebuilds `outputs/screenshots/` from the current figures. If you re-run
the pipeline and the charts change, re-run this and the pack updates.
