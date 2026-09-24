# outputs/figures/powerbi/

**There are no Power BI screenshots in this folder, because none were taken.**

Power BI Desktop is a Windows-only application. The environment in which this project was built is
Linux, so Power BI could not be installed, automated or screenshotted here. Rather than present
something else as a Power BI screenshot, this folder contains:

## `mockups/` - design mockups (not screenshots)

Ten PNGs rendered with matplotlib **from the real extracts in `powerbi/data/`**. Every number on
them is an actual project output. Each one is watermarked:

> DESIGN MOCKUP - layout specification drawn from the real data. Not a Power BI screenshot.

| File | Page |
|---|---|
| `00_home_mockup.png` | HOME |
| `01_executive_overview_mockup.png` | 1 Executive Overview |
| `02_revenue_intelligence_mockup.png` | 2 Revenue Intelligence |
| `03_customer_intelligence_mockup.png` | 3 Customer Intelligence |
| `04_customer_segmentation_mockup.png` | 4 Customer Segmentation |
| `05_product_analytics_mockup.png` | 5 Product Analytics |
| `06_regional_analytics_mockup.png` | 6 Regional Analytics |
| `07_prediction_forecast_mockup.png` | 7 Prediction & Forecast |
| `08_business_recommendations_mockup.png` | 8 Business Recommendations |
| `09_customer_detail_drillthrough_mockup.png` | Customer Detail (drill-through) |

They serve as the layout specification for the build: chart types, positions, titles, labels and
theme are all as the finished page should look.

## What has to be done manually

1. Build the report in Power BI Desktop on a Windows machine, following
   `powerbi/POWERBI_BUILD_GUIDE.md` (11 steps, ~3-4 hours).
2. Validate the cards against `powerbi/validation/measure_validation_targets.csv`.
3. Capture one screenshot per page, with the slicers cleared, and save them **in this folder** as:

```
01_executive_overview.png      05_product_analytics.png
02_revenue_intelligence.png    06_regional_analytics.png
03_customer_intelligence.png   07_prediction_forecast.png
04_customer_segmentation.png   08_business_recommendations.png
```

4. Optionally export the whole report to PDF (File > Export > Export to PDF) and save it as
   `outputs/reports/powerbi_dashboard.pdf`.
5. Update `outputs/tables/powerbi_validation_checklist.csv`, changing the status of the page items
   from "Specified + mockup" to "Built in Power BI Desktop" as each one is genuinely finished.

Until step 3 is done, this folder contains mockups only - and says so.
