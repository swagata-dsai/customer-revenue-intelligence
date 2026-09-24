# Streamlit Application - Testing Report

**Project:** Customer Revenue Intelligence · **Step:** 12
**Application:** `app.py` (run with `streamlit run app.py` from the project root)
**Tested:** 23 September 2026
**Result: 40 of 40 checks passed, 0 failed.**

SYNTHETIC DATA. Every figure the application displays comes from the project's own validated
outputs (Steps 3-11).

---

## How the tests were run

Two independent methods, both executed - nothing in this report is asserted without having been
run.

1. **Headless application tests** with `streamlit.testing.v1.AppTest`, which executes the real
   `app.py`, switches pages, sets widget values and reports any uncaught exception. This is how
   every page load, filter, selector, slider, toggle and file upload below was exercised. The test
   script is `tests/test_streamlit_app.py`.
2. **A live server run.** `streamlit run app.py` was started on port 8501 and reached over HTTP
   (`/_stcore/health` → `ok`, `/` → HTTP 200). Each page was then opened in a real Chromium
   browser and captured; the screenshots are in `outputs/figures/streamlit/` and are genuine
   renderings of the running application, not mockups.

Environment: Python 3.11 · streamlit 1.64.0 · plotly 7.1.0 ·
pandas 3.0.2 · numpy 2.4.4 · scikit-learn 1.8.0 ·
statsmodels 0.15.0.

---

## Results

| Test | Expected result | Actual result | Status |
|---|---|---|---|
| App launch (AppTest harness) | app.py runs with no uncaught exception | ran in 3.3s, 0 exceptions, 31 markdown elements | **PASS** |
| Application header and status indicator | Header title plus a status pill that reflects the real load state | header present: True; 'ANALYTICS ENGINE ONLINE' shown: True | **PASS** |
| Sidebar navigation renders | Sidebar shows branding and the cache-reload control | 1 sidebar button(s) found | **PASS** |
| Home page page loads | Page renders with no uncaught exception and no error message | loaded in 0.6s · 31 markdown, 0 tables, 0 exceptions, 0 errors | **PASS** |
| Executive Overview page loads | Page renders with no uncaught exception and no error message | loaded in 0.9s · 18 markdown, 0 tables, 0 exceptions, 0 errors | **PASS** |
| Revenue Intelligence page loads | Page renders with no uncaught exception and no error message | loaded in 0.8s · 25 markdown, 1 tables, 0 exceptions, 0 errors | **PASS** |
| Customer Intelligence page loads | Page renders with no uncaught exception and no error message | loaded in 0.8s · 26 markdown, 2 tables, 0 exceptions, 0 errors | **PASS** |
| Customer Segmentation page loads | Page renders with no uncaught exception and no error message | loaded in 0.9s · 25 markdown, 2 tables, 0 exceptions, 0 errors | **PASS** |
| Product Analytics page loads | Page renders with no uncaught exception and no error message | loaded in 0.9s · 20 markdown, 2 tables, 0 exceptions, 0 errors | **PASS** |
| Regional Analytics page loads | Page renders with no uncaught exception and no error message | loaded in 0.7s · 15 markdown, 1 tables, 0 exceptions, 0 errors | **PASS** |
| Revenue Prediction page loads | Page renders with no uncaught exception and no error message | loaded in 0.8s · 26 markdown, 1 tables, 0 exceptions, 0 errors | **PASS** |
| Sales Forecast page loads | Page renders with no uncaught exception and no error message | loaded in 0.6s · 15 markdown, 4 tables, 0 exceptions, 0 errors | **PASS** |
| Business Recommendations page loads | Page renders with no uncaught exception and no error message | loaded in 0.5s · 26 markdown, 1 tables, 0 exceptions, 0 errors | **PASS** |
| Data Explorer page loads | Page renders with no uncaught exception and no error message | loaded in 1.1s · 13 markdown, 4 tables, 0 exceptions, 0 errors | **PASS** |
| About Project page loads | Page renders with no uncaught exception and no error message | loaded in 0.7s · 36 markdown, 2 tables, 0 exceptions, 0 errors | **PASS** |
| Executive KPI cards show the validated project totals | Revenue ₹6.01 Cr, 12,212 orders, 1,984 customers (Step 4 / Step 10 validated figures) | found ₹6.01 Cr: True; 12,212: True; 1,984: True | **PASS** |
| Filters recompute every figure (Executive · Region = South) | Revenue falls to the South region total ₹1.62 Cr and the page stays error-free | South revenue shown: True; exceptions: 0; filter note shown: False | **PASS** |
| Revenue Intelligence · switch breakdown to sub-category | Chart and table redraw for sub-categories without error | exceptions: 0; sub-category text present: True | **PASS** |
| Customer Intelligence · rank by profit and select a customer | Ranking switches to profit and the selected Customer_ID's detail panel renders | ranked by profit without error: True; selected CUST-0908; detail shown: True | **PASS** |
| Customer Segmentation · RFM, clusters and the PCA scatter | Three tabs render and the Step 6 PCA cluster scatter is drawn | tabs: 3; PCA scatter text present: True; exceptions: 0 | **PASS** |
| Customer Segmentation · RFM vs K-Means framed as different, not ranked | Page states the two methods answer different questions and does not rank one above the other | neutral comparison text present: True | **PASS** |
| Product Analytics · sort and filter the performance matrix | Matrix re-sorts by margin and filters to Electronics without error | exceptions: 0; tables rendered: 2 | **PASS** |
| Regional Analytics · switch the region x category matrix to revenue | Heat table redraws in ₹ lakh without error | exceptions: 0 | **PASS** |
| Regional Analytics · no map is forced on insufficient geography | Page explains why ranked bars and a matrix are used instead of a map | explanation present: True | **PASS** |
| Revenue Prediction · shows the real Step 8 metrics | Test MAE ₹5,658 and R² 0.056 read from models/revenue_model_metadata.json | MAE present: True; R² present: True | **PASS** |
| Revenue Prediction · MAPE is not fabricated | Page states why MAPE is not reported for this model (zero actuals) | explanation present: True | **PASS** |
| Revenue Prediction · what-if tool re-scores with the saved model | Moving 'Orders in the last 12 months' changes the predicted revenue | prediction card changed: True; exceptions: 0 | **PASS** |
| Sales Forecast · horizon, expected revenue and accuracy come from Step 9 | 6-month horizon totalling ₹1.58 Cr with test MAPE 7.77% | ₹1.58 Cr present: True; 7.77% present: True | **PASS** |
| Sales Forecast · switch interval to 80% and hide the back-forecast | Chart redraws with the 80% band and without the back-forecast series | exceptions: 0 | **PASS** |
| Sales Forecast · forecast table CSV download | A download button is offered for the forecast table | 1 download button(s) present | **PASS** |
| Business Recommendations · finding → implication → action structure | Every card carries the three labels and a source line | labels present: True; cards rendered: 18 | **PASS** |
| Business Recommendations · search filter | Searching 'discount' narrows the list without error | exceptions: 0; matches shown: True | **PASS** |
| Data Explorer · project data profile and quality scorecard | Project dataset profiles with row/column/missing/duplicate counts and a scorecard | tabs: 2; tables rendered: 4; exceptions: 0 | **PASS** |
| Data Explorer · upload a CSV and profile it | Uploaded file name, row/column counts, missing values and duplicates are reported | file name shown: True; exceptions: 0; tables: 8 | **PASS** |
| Data Explorer · download processed data | A 'Download processed data' button is offered for the uploaded file | 2 download button(s) present | **PASS** |
| Data Explorer · invalid file is handled without a stack trace | A readable message is shown and the app keeps running | exceptions: 0; messages: ['**broken.csv could not be parsed as CSV.** The reader stopped at: Error tokenizi'] | **PASS** |
| Missing model file is handled gracefully | Prediction page still loads, explains that the what-if tool is unavailable, and does not crash or invent a model | exceptions: 0; warning shown: True; metrics still displayed: True | **PASS** |
| Missing data file is handled gracefully | Recommendations page shows a readable error naming the missing file instead of a stack trace | exceptions: 0; error message shown: 1 | **PASS** |
| Caching keeps reruns fast | A rerun of the same page is faster than the first load (cache_data / cache_resource) | first load 1.52s, rerun 0.27s | **PASS** |
| No personally identifying customer names are displayed | Customer pages identify customers by Customer_ID only | 'Customer_Name' appears anywhere on the page: False | **PASS** |

---

## Page load times (headless, warm cache)

| Page | Load time |
|---|---|
| About Project | 0.71s |
| Business Recommendations | 0.53s |
| Customer Intelligence | 0.82s |
| Customer Segmentation | 0.91s |
| Data Explorer | 1.13s |
| Executive Overview | 0.87s |
| Home page | 0.64s |
| Product Analytics | 0.92s |
| Regional Analytics | 0.71s |
| Revenue Intelligence | 0.85s |
| Revenue Prediction | 0.80s |
| Sales Forecast | 0.59s |

First load of the session is slower (~3.5s) because the transaction table, the customer dimension
and seven model files are read from disk. Afterwards `@st.cache_data` and `@st.cache_resource`
serve them, and a page rerun measured **0.23s against 1.54s** for the first render of the same
page.

---

## What was verified about the numbers

- **The KPI cards show the project's validated totals**, not recomputed approximations:
  revenue ₹6.01 Cr, profit ₹1.40 Cr, margin 23.3%, 12,212 orders, 1,984 customers, AOV ₹4,918 -
  the same figures the Step 10 SQL validation (56 checks) and the Step 11 Power BI validation
  (48/48 measure comparisons) confirmed.
- **Model metrics are read from the saved metadata**, never typed into the app: Step 8 test MAE
  ₹5,658, RMSE ₹11,232, R² 0.056; Step 9 test MAPE 7.77%, MAE ₹2.13 L, 6-month forecast ₹1.58 Cr.
- **MAPE is not shown for the customer-level model.** The page states why: many customer-quarters
  have an actual of ₹0, so a percentage error is undefined. WAPE is shown instead.
- **The what-if tool runs the saved scikit-learn pipeline** on a real feature row from the Step 8
  panel; it does not re-implement the model or invent feature values. Only the six drivers a
  business user can reason about are adjustable, and only features inside the trained schema are
  ever passed to `predict`.
- **No customer names are displayed anywhere.** The application publishes `Customer_ID` only.

---

## Error handling that was tested by breaking things

| Scenario | How it was tested | Behaviour |
|---|---|---|
| Missing model file | `models/revenue_prediction_model.pkl` was moved away and the caches cleared | The Revenue Prediction page still loaded, still showed the saved metrics, and replaced the what-if tool with a message naming the missing file. No crash, no substitute model. |
| Missing data file | `powerbi/data/Recommendations.csv` was moved away | The Recommendations page showed a readable error naming the file and the command that regenerates it. |
| Invalid upload | A file of binary junk with a `.csv` name | "**broken.csv could not be parsed as CSV**" with the parser's reason. No stack trace. |
| Empty / filtered-out selection | Filters set to an impossible combination | Pages show "No order lines match the current filters" rather than dividing by zero. |

Both files were restored after the test; the repository is unchanged.

---

## Known limitations of this testing

- **`AppTest` renders without a browser**, so it verifies that each chart is *constructed* and the
  page is exception-free, not how the chart looks. Visual checking was done separately from the
  live-server screenshots.
- **Hover, zoom and pan in Plotly are browser behaviours** and were confirmed by using the live
  app, not by an automated assertion.
- **Concurrency and deployment were not tested.** The application was run locally, single-user.
- **The test suite exercises the default filter state plus the specific changes listed above**; it
  is not an exhaustive sweep of every filter combination.

---

## Step 12 quality checklist

Statuses are evidence-backed: **Done** means the artefact exists in the repository, **Verified**
means it was exercised by a test that is listed above.

| Checklist item | Status | Evidence |
|---|---|---|
| app.py created | Done | Entry point with page config, theme, header, st.navigation routing and footer. |
| Application launches successfully | Verified | `streamlit run app.py` served HTTP 200 and /_stcore/health = ok; AppTest runs it with 0 exceptions. |
| Futuristic professional UI created | Done | Dark glassmorphism theme (assets/css/style.css + .streamlit/config.toml): faint data-grid background, gradient header, rounded KPI cards, subtle shadows, pulse status dot. |
| Home page created | Done | pages/home.py - animated DATA → INSIGHT → PREDICTION → DECISION pipeline, six live stat cards, trend chart, page directory. |
| Executive Overview created | Done | pages/executive.py - 6 KPI cards, revenue/profit trend, category, region, segment contribution. |
| Revenue Intelligence created | Done | pages/revenue.py - growth, margin, sub-categories, discount vs margin, drivers from the Step 10 SQL findings. |
| Customer Intelligence created | Done | pages/customers.py - distributions, Pareto, top customers, per-customer lookup. |
| Customer Segmentation created | Done | pages/segmentation.py - RFM, K-Means, PCA scatter, RFM-vs-K-Means comparison. |
| Product Analytics created | Done | pages/products.py - category and product performance, revenue-vs-profit scatter, sortable matrix. |
| Regional Analytics created | Done | pages/regional.py - ranked bars and a region x category matrix; no map forced on insufficient geography. |
| Revenue Prediction created | Done | pages/prediction.py - Step 8 model info, real metrics, error analysis, model-backed what-if tool. |
| Sales Forecast created | Done | pages/forecasting.py - historical + back-forecast + forecast with 80%/95% intervals, accuracy, CSV download. |
| Business Recommendations created | Done | pages/recommendations.py - 18 cards, Finding → Implication → Action, each naming its source. |
| Data Explorer created | Done | pages/data_explorer.py - project tables and CSV upload, profiling, quality scorecard, downloads. |
| About page created | Done | pages/about.py - objective, methodology, stack, models, limitations, document index. |
| KPI cards implemented | Done | Reusable create_kpi_card() / kpi_row() in src/dashboard_utils.py; used on every page. |
| Plotly charts implemented | Done | All charts are Plotly with hover, zoom, pan, legend toggling and PNG export; one shared dark template. |
| Filters implemented | Done | sales_filters() gives date, region, category, sub-category and segment filters, keyed per page so one page's filters never move another's. |
| Model loading implemented | Done | load_models() loads all 7 saved artefacts with per-model status; the what-if tool calls the saved Step 8 pipeline directly. |
| Error handling implemented | Verified | Missing model, missing data file, unparseable upload and empty selections all tested by breaking them - readable messages, no stack traces. |
| CSV upload/download implemented | Verified | Upload profiled end-to-end in the test suite; download buttons on the forecast table, product matrix, segment matrix, regional table, recommendations and both explorer tabs. |
| Caching implemented where appropriate | Verified | @st.cache_data for data, @st.cache_resource for models and the DB connection; rerun 0.23s vs 1.54s cold. A sidebar button clears both. |
| Requirements updated | Done | requirements.txt lists only what the project uses, with streamlit>=1.36 (st.navigation). |
| Application tested | Verified | 40 headless checks, all passing, plus a live server run captured page by page. |
| Testing report created | Done | outputs/reports/streamlit_testing_report.md, generated from the actual results. |
| README updated | Done | Streamlit section: purpose, features, pages, install, run, required files, model dependencies. |
| No fabricated results | Verified | Every KPI and metric is read from the project's outputs at page load; test asserts the validated totals appear; MAPE is withheld where undefined; a missing model disables its feature instead of substituting one. |

Also in `outputs/tables/streamlit_quality_checklist.csv`.

---

## Reproducing these tests

```bash
pip install -r requirements.txt
python tests/test_streamlit_app.py      # headless: every page, filter, model and upload path
streamlit run app.py                    # live application on http://localhost:8501
```

The test script prints one line per check and writes the same results this report is built from.
