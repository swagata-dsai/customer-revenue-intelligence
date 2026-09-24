# Power BI build guide (manual steps)

**Read this first.** Power BI Desktop runs only on Windows and could not be installed or automated
in the environment where this project was built, so **the `.pbix` file does not exist yet**. Every
input it needs does exist and has been validated. This guide is the exact list of steps that have to
be performed by hand in Power BI Desktop, in order. Nothing in this project claims that any of these
steps has already been done.

Estimated time: 3-4 hours for the full eight-page report.

---

## 0. Before you start

- Install **Power BI Desktop** (free, Microsoft Store).
- Copy the whole `powerbi/` folder to the Windows machine, or open the project folder from it.
- Have these open: `powerbi/dax/measures.dax`, `powerbi/relationships.csv`,
  `powerbi/validation/measure_validation_targets.csv`, and the mockups in
  `outputs/figures/powerbi/mockups/`.

---

## 1. Apply the theme (2 minutes)

**View > Themes > Browse for themes** > `powerbi/theme/crm_dark_theme.json`.

Then **Insert > Image** `powerbi/theme/page_background.png` on each page, sent to the back, or set
it as the page background (Format page > Canvas background > Image, Fit, 0% transparency).

## 2. Load the data (15 minutes)

1. **Home > Get data > Blank query**, name it `DataFolder`, and paste
   `powerbi/powerquery/00_DataFolder_parameter.m` into the advanced editor. Convert it to a
   parameter (**Manage parameters**) and set it to the full path of `powerbi/data/` **with a
   trailing backslash**.
2. For each table below, **New source > Blank query > Advanced editor**, paste the matching `.m`
   file, and name the query exactly as the table name.

| # | Extract | Power Query script |
|---|---|---|
| 1 | `DimDate.csv` | `powerbi/powerquery/DimDate.m` |
| 2 | `DimGeography.csv` | `powerbi/powerquery/DimGeography.m` |
| 3 | `DimProduct.csv` | `powerbi/powerquery/DimProduct.m` |
| 4 | `DimRFMSegment.csv` | `powerbi/powerquery/DimRFMSegment.m` |
| 5 | `DimCluster.csv` | `powerbi/powerquery/DimCluster.m` |
| 6 | `DimCustomer.csv` | `powerbi/powerquery/DimCustomer.m` |
| 7 | `FactSales.csv` | `powerbi/powerquery/FactSales.m` |
| 8 | `FactForecast.csv` | `powerbi/powerquery/FactForecast.m` |
| 9 | `FactRevenuePrediction.csv` | `powerbi/powerquery/FactRevenuePrediction.m` |
| 10 | `PredictionQuarterly.csv` | `powerbi/powerquery/PredictionQuarterly.m` |
| 11 | `ModelMetrics.csv` | `powerbi/powerquery/ModelMetrics.m` |
| 12 | `ModelInfo.csv` | `powerbi/powerquery/ModelInfo.m` |
| 13 | `Recommendations.csv` | `powerbi/powerquery/Recommendations.m` |

3. **Close & Apply.**

## 3. Set up the date table (5 minutes)

1. Select `DimDate` > **Table tools > Mark as date table** > `Date`.
2. `DimDate[Month_Name]` > **Column tools > Sort by column** > `Month_Number`.
3. Repeat: `Year_Month` sorted by `Year_Month_Sort`; `Year_Quarter` by `Year_Quarter_Sort`;
   `Month_Short` by `Month_Number`; `Day_Name` by `Day_Of_Week_Number`.
4. `DimRFMSegment[RFM_Segment]` sorted by `Segment_Order`; `DimCluster[Cluster_Label]` by
   `Cluster_Order`; `DimCustomer[Recency_Band]` by `Recency_Band_Order`;
   `DimCustomer[Frequency_Band]` by `Frequency_Band_Order`; `DimCustomer[Activity_Status]` by
   `Activity_Status_Order`; `FactSales[Discount_Band]` by `Discount_Band_Order`.

## 4. Build the relationships (10 minutes)

**Model view**, delete every relationship Power BI guessed, then create these by hand exactly as
listed in `powerbi/relationships.csv`:

| From Table | From Column | To Table | To Column | Cardinality | Cross Filter Direction | Active |
|---|---|---|---|---|---|---|
| DimDate | Date | FactSales | Order_Date | One-to-many | Single | Yes |
| DimCustomer | Customer_ID | FactSales | Customer_ID | One-to-many | Single | Yes |
| DimProduct | Product_ID | FactSales | Product_ID | One-to-many | Single | Yes |
| DimGeography | Location_ID | FactSales | Location_ID | One-to-many | Single | Yes |
| DimRFMSegment | RFM_Segment | DimCustomer | RFM_Segment | One-to-many | Single | Yes |
| DimCluster | Cluster_ID | DimCustomer | Cluster_ID | One-to-many | Single | Yes |
| DimDate | Date | FactForecast | Month_Date | One-to-many | Single | Yes |
| DimDate | Date | FactRevenuePrediction | Target_Quarter_Start | One-to-many | Single | No |
| DimCustomer | Customer_ID | FactRevenuePrediction | Customer_ID | One-to-many | Single | Yes |

Leave `DimDate -> FactRevenuePrediction` **inactive** - that is deliberate (see documentation
section 4).

Hide from report view: every key column (`Location_ID`, the `*_Order` sort columns,
`Year_Month_Sort`, `Year_Quarter_Sort`) so report users only see fields they can use.

## 5. Add the measures (30 minutes)

1. **Home > Enter data**, one column, name the table `_Measures`, Load, then delete the dummy
   column. Move `_Measures` to the top of the field list.
2. Paste each measure from `powerbi/dax/measures.dax` into a new measure on `_Measures`.
3. For each, set the **Display folder** and **Format** shown in the comment above it.
   (84 measures in 10 folders.)

## 6. Validate before building any visual (15 minutes)

Do this now, not at the end - a wrong measure caught here saves rebuilding pages.

1. Put a table visual on a blank page with `Total Revenue`, `Total Profit`, `Profit Margin %`,
   `Total Orders`, `Total Customers`, `Average Order Value`.
2. Compare with the "All data" rows of `powerbi/validation/measure_validation_targets.csv`.
3. Add `DimDate[Year]`, then `DimGeography[Region]`, then `DimProduct[Category]`, then
   `DimRFMSegment[RFM_Segment]` and check those contexts too.
4. Record what Power BI shows in the `Power_BI_Value` column of that file.
5. If you have DAX Studio, run `powerbi/dax/validation_query.dax` instead - it produces all of it
   at once.

A difference of more than ₹1 means a measure does not match the SQL; fix the measure before
continuing.

## 7. Build the pages (2-3 hours)

Work from the mockups in `outputs/figures/powerbi/mockups/` and the page specifications in
`outputs/reports/powerbi_dashboard_documentation.md` section 6. For each page:

1. Set the page size to 16:9 (1280 x 720) and apply the background.
2. Add the header: page title text box, `Date Range Label` and `Filters Applied` as cards.
3. Add the slicer row and set each slicer's field and style.
4. Add the visuals in the order the specification lists them, using the stated chart type.
5. Give every visual the title the specification gives it - a sentence, not a field name.
6. Turn off the visual header, keep the theme's panel background and border.

Then **View > Sync slicers** and set the sync groups from documentation section 8.

## 8. Drill-through and tooltips (20 minutes)

1. New page **Customer Detail**: set page information > **Allow use as drill-through**, drill-through
   field `DimCustomer[Customer_ID]`, "Keep all filters" on. Build it from mockup 09. Add the back
   button.
2. New page **Product Detail**: same, on `DimProduct[Product_ID]`.
3. New pages **Customer tooltip** and **Product tooltip**: page size **Tooltip** (320 x 240), page
   information > **Allow use as tooltip** on. Then, on each customer or product visual, Format >
   Tooltip > Report page > pick the tooltip page.
4. Hide all four pages from the page tabs (right-click the tab > Hide page).

## 9. Navigation (15 minutes)

1. On HOME, add a button per page: **Insert > Buttons > Blank**, set Action > Page navigation.
2. Copy the navigation rail to every page (select the buttons, copy, paste on each page) so it sits
   in the same position everywhere.
3. Add a **Reset filters** button: set the default state, **View > Bookmarks > Add**, name it
   "Default view", then point the button's action at that bookmark.

## 10. Take the screenshots (10 minutes)

The screenshots referred to in the brief have to be captured here, from the finished report. Save
them to `outputs/figures/powerbi/` under exactly these names:

```
01_executive_overview.png      05_product_analytics.png
02_revenue_intelligence.png    06_regional_analytics.png
03_customer_intelligence.png   07_prediction_forecast.png
04_customer_segmentation.png   08_business_recommendations.png
```

Use **File > Export > Export to PDF** for the whole report as well, and the Windows Snipping Tool
(Win+Shift+S) or **View > Full screen** then Print Screen for individual pages. Capture each page
with the slicers cleared, so the screenshots show full-period figures.

## 11. Final checks

- [ ] Every card matches `powerbi/validation/measure_validation_targets.csv`
- [ ] No visual shows "(Blank)" in a segment or cluster slicer
- [ ] Month names sort January…December, not alphabetically
- [ ] No chart has two y-axes
- [ ] Every visual title is a sentence that says what the visual shows
- [ ] The synthetic-data statement appears on HOME and the Executive Overview
- [ ] No customer name appears anywhere
- [ ] Save as `powerbi/CustomerRevenueIntelligence.pbix`

Update `outputs/tables/powerbi_validation_checklist.csv` as you complete each item, so the project's
record of what was actually done stays honest.
