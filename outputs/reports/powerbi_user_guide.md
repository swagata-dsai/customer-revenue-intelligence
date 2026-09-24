# Power BI Dashboard - User Guide

**Customer Revenue Intelligence** · Step 11
**The data in this report is synthetic**: it was generated for an internship project and does not
describe real customers or a real company.

This guide is for reading the dashboard, not for building it. If you need to build or rebuild the
report file, use `powerbi/POWERBI_BUILD_GUIDE.md`.

---

## 1. Opening the dashboard

1. Install **Power BI Desktop** (free, Windows only) from the Microsoft Store, or open the report in
   the Power BI Service if it has been published.
2. Open `powerbi/CustomerRevenueIntelligence.pbix`.
3. If Power BI asks about the data source, point the **DataFolder** parameter at the folder holding
   the CSV extracts (**Transform data > Edit parameters**, then **Refresh**). The folder is
   `powerbi/data/` inside the project.
4. The report opens on **HOME**.

You do not need Python, SQL or the database to read the report: the data travels inside the file.

---

## 2. Getting around

The navigation rail runs down the left of every page: **HOME** and the eight pages, with the current
page highlighted. Click a page name to go there, or use the HOME page's directory.

| Page | Use it when you want to know |
|---|---|
| 1 Executive Overview | The headline position: revenue, profit, margin, orders, customers, AOV, and where they come from |
| 2 Revenue Intelligence | How revenue and margin are moving, and which sub-categories and discount levels drive them |
| 3 Customer Intelligence | How customer value is distributed, who the top customers are, how recently people bought |
| 4 Customer Segmentation | How the rule-based segments and the machine-learning clusters describe the base |
| 5 Product Analytics | Which products earn, which only turn over, which lose value to returns |
| 6 Regional Analytics | How each region performs and why |
| 7 Prediction & Forecast | What the two models expect next, and how accurate they have been |
| 8 Business Recommendations | What to do about all of it, with the evidence attached |

**Back from a drill-through:** click the back arrow at the top left of the detail page, or press
Ctrl and click it.

---

## 3. Using the slicers

The slicer row sits under the page title. The slicers are **synced**: choosing Region = South on the
Executive Overview keeps South selected when you move to Product Analytics.

| Slicer | What it does |
|---|---|
| Date | Restricts every transaction figure to a date range |
| Year / Month | Quicker versions of the same thing |
| Region | One or more of North, South, East, West, Central |
| Category / Sub-category | Product groups; Sub-category follows the Category you picked |
| Customer segment | The RFM segments (Champions, Loyal Customers, At Risk, …) |
| Cluster | The four K-Means clusters |

Tips:

- Ctrl-click to select more than one value.
- The header shows the selected date range and a note when dimension filters are applied, so you can
  always tell whether you are looking at everything or at a slice.
- Clicking a bar or a segment also filters the rest of the page (cross-filtering). Click it again,
  or click empty space, to release it.

---

## 4. Resetting filters

- **One slicer:** click the eraser icon in its top-right corner.
- **The whole page:** use the **Reset filters** button in the page header (it is a bookmark that
  restores the default state).
- **Everything, including cross-filters:** Home ribbon > **Reset to default** in the Power BI
  Service, or reopen the file in Desktop.

---

## 5. Drilling into a customer or a product

Right-click a row in the top-customer table, a segment in the matrix or a bar in a product chart,
then choose **Drill through > Customer Detail** (or **Product Detail**).

The detail page shows that one customer or product: its profile, lifetime revenue and profit, its
monthly pattern, its category mix and its recent orders. Customers are identified by **Customer_ID**
only - no customer names appear anywhere in this report.

Hovering over most visuals shows a tooltip card with the same figures in miniature, without
leaving the page.

---

## 6. Reading the KPIs

| KPI | What it means | Full-period value |
|---|---|---|
| Total Revenue | Value of **delivered** order lines. Returned and Cancelled lines are excluded | ₹6.01 Cr |
| Total Profit | Revenue minus cost of goods on those lines | ₹1.40 Cr |
| Profit Margin % | Profit / revenue | 23.3% |
| Total Orders | Orders with at least one delivered line | 12,212 |
| Total Customers | Customers with at least one delivered order | 1,984 |
| Average Order Value | Revenue / orders | ₹4,918 |
| Active Customers | Customers whose last delivered purchase was under 180 days before 2026-01-01 | 1,288 |

Three things worth knowing:

1. **Revenue means delivered revenue.** The gap between what was booked and what was delivered
   (9.4% of booked value) is shown separately on the Revenue Intelligence and Product Analytics
   pages.
2. **"Active" and "inactive" are about recency, not churn.** No customer is labelled as churned
   anywhere in this project, because no churn event is defined for this data.
3. **Customer figures are a snapshot.** Segments, recency, frequency and customer value were
   calculated once, at the reference date 2026-01-01. They do not change when you move the Date
   slicer - the transaction figures next to them do. This is deliberate, and the measure tooltips
   say so.

Numbers are shown in Indian units: **Cr** = crore (10,000,000) and **L** = lakh (100,000). Chart
axes are usually in ₹ lakh to keep the labels short.

---

## 7. Reading the forecast and the prediction

Page 7 shows two different models. They are never added together.

**FORECAST (green)** - total company revenue for the next 6 months
(2026-01 to 2026-06). The shaded band is the 95% prediction
interval: the model's own statement of how uncertain it is. The band widens as the horizon
lengthens, because month 6 is less certain than month 1. Plan to the line, stress-test to the lower
edge.

How accurate has it been? On six months it had never seen, its average error was
7.77% (MAE ₹2.13 L). The dashed
orange line on the chart is exactly that test: the model's forecast for months it was not trained
on, drawn against what actually happened.

**PREDICTED (orange)** - the machine-learning estimate of how much an *individual customer* will
spend in the next quarter. Use it to **rank** customers for outreach and as an aggregate planning
figure. Do not quote one customer's predicted revenue as a commitment: the model's R² at customer
level is 0.056, which is better than the baselines but far from precise for one person.

**HISTORICAL (blue)** is always actual delivered revenue.

---

## 8. Refreshing the data

The report reads CSV extracts, so refreshing is two steps:

1. **Regenerate the extracts** (needs Python and the project):
   ```bash
   cd customer-revenue-intelligence
   python -c "from src.powerbi_prep import run_powerbi_prep; run_powerbi_prep()"
   ```
   If the underlying data has changed, rerun the pipeline first (Steps 3-10), then the command
   above.
2. **Refresh in Power BI**: Home ribbon > **Refresh**. If the files moved, update the **DataFolder**
   parameter first (Transform data > Edit parameters).

After a refresh, sanity-check three cards against
`powerbi/validation/measure_validation_targets.csv`: Total Revenue, Total Orders and Total
Customers. If they match, the model loaded correctly.

---

## 9. If something looks wrong

| What you see | Usual reason |
|---|---|
| Every number is blank | A slicer combination with no rows - clear the filters |
| Revenue looks too low | The Date slicer, or a Region / Category filter, is still applied - check the header |
| A customer count does not change with the date range | Expected: customer-state measures are a 2026-01-01 snapshot |
| A "(Blank)" row in a segment slicer | Should not happen - customers with no delivered order show as "No delivered order" |
| The forecast line stops | The Date slicer ends before 2026-06-30; extend it to see the whole horizon |
