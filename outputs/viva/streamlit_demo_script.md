# Streamlit Demonstration Script

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

A working **12-page** application.
**40/40** headless tests pass. Start it with:

```bash
streamlit run app.py        # http://localhost:8501
```

## The architectural point to make first

The application is a **presentation layer**. It loads the same persisted `.pkl`
models and the same output files the pipeline wrote, and it computes no metric
of its own — every number comes from the pipeline's outputs or from the shared
module the pipeline itself uses. That is why a figure on screen cannot drift
from the report.

## Page by page

### Home  ·  `pages/home.py`

- **Purpose.** Entry point: what the platform is, dataset status, how to navigate
- **Input.** None — it reads the data-status check at start-up
- **Processing.** Checks whether the database and each model artefact are present
- **Visualisation.** Status pill, the pipeline flow, page cards
- **Business value.** Tells the user immediately whether anything is missing before they trust a number

### Executive Overview  ·  `pages/executive.py`

- **Purpose.** The monthly position in one screen
- **Input.** Date range, region, category, segment filters
- **Processing.** Reads cached KPIs from the shared loader; no metric computed on the page
- **Visualisation.** KPI cards, monthly revenue and profit line, revenue by region and category
- **Business value.** A manager sees the position in fifteen seconds

### Revenue Intelligence  ·  `pages/revenue.py`

- **Purpose.** Decompose revenue and profit across dimensions
- **Input.** Date range, category, discount band, payment method
- **Processing.** Groups the delivered lines by the selected dimension
- **Visualisation.** Revenue over time, category and sub-category bars, discount-band margin, payment-method outcomes, order-status value
- **Business value.** Separates what earns from what merely turns over

### Customer Intelligence  ·  `pages/customers.py`

- **Purpose.** Understand the customer base rather than the transaction base
- **Input.** Date range, region, segment
- **Processing.** Customer-level rollup from the delivered lines
- **Visualisation.** Concentration curve, revenue-per-customer distribution, repeat versus single purchase, tenure against value
- **Business value.** Shows that the top 10% of customers produce {top10} of revenue

### Customer Segmentation  ·  `pages/segmentation.py`

- **Purpose.** RFM segments and K-Means clusters side by side
- **Input.** Segment, cluster, recency and value band; an at-risk high-value toggle
- **Processing.** Loads the persisted K-Means model and scaler; joins the RFM and cluster assignments
- **Visualisation.** Segment revenue bars, cluster profiles, the RFM-versus-cluster cross-tab, the at-risk table
- **Business value.** Produces the {at_risk}-customer working list holding {at_risk_rev}

### Product Analytics  ·  `pages/products.py`

- **Purpose.** Separate volume leaders from margin leaders
- **Input.** Category, sub-category, date range
- **Processing.** Product-level aggregation with margin and return rate
- **Visualisation.** Category revenue versus profit, sub-category margin ranking, the product quadrant, top-N tables
- **Business value.** {top_cat} leads volume at {top_cat_margin} margin while {best_cat} earns {best_cat_margin}

### Regional Analytics  ·  `pages/regional.py`

- **Purpose.** Geography performance and the region × category margin test
- **Input.** Region, state, category
- **Processing.** Regional aggregation plus the pairwise margin comparison against the national figure
- **Visualisation.** Revenue and profit by region, state and city rankings, the region × category matrix
- **Business value.** Rules out a regional margin problem: {region_gaps} of {region_pairs} pairs more than 2 pp below national

### Revenue Prediction  ·  `pages/prediction.py`

- **Purpose.** Next-quarter customer revenue, shown with its own accuracy
- **Input.** Segment, cluster, revenue band
- **Processing.** Loads `revenue_prediction_model.pkl` and its preprocessor and applies them to the prepared panel — it does not refit
- **Visualisation.** Actual versus predicted scatter, error distribution, predictions by segment, the metrics panel
- **Business value.** Usable at portfolio level (bias {pred_bias}), explicitly not per customer (R² {pred_r2})

### Sales Forecast  ·  `pages/forecasting.py`

- **Purpose.** Six-month company revenue forecast with uncertainty
- **Input.** Interval width (80% / 95%), history window
- **Processing.** Loads `forecasting_model.pkl` and reads the persisted forecast table
- **Visualisation.** History with the forecast and shaded intervals, the backtest position, the model comparison
- **Business value.** Plan against the interval {fc_low}–{fc_high}, not the {fc_total} point estimate

### Business Recommendations  ·  `pages/recommendations.py`

- **Purpose.** The action list, with evidence attached
- **Input.** Area filter
- **Processing.** Reads the recommendations table generated by the pipeline
- **Visualisation.** {{pbi_recs}} cards, each with finding, evidence, metric, value and analytical source
- **Business value.** Every recommendation is traceable to the analysis that produced it

### Data Explorer  ·  `pages/data_explorer.py`

- **Purpose.** Direct, filterable access to the underlying tables
- **Input.** Table selector, column filters, a CSV upload for schema validation
- **Processing.** Applies filters to the selected DataFrame; validates an uploaded file's columns against the expected schema
- **Visualisation.** Paged table view with a CSV download button
- **Business value.** Lets an examiner check any number themselves

### About the Project  ·  `pages/about.py`

- **Purpose.** Methodology, model metadata, limitations and reproduction steps
- **Input.** None
- **Processing.** Reads the persisted model metadata files
- **Visualisation.** Method summary, model cards with metrics and selection rules, the limitations list
- **Business value.** Puts the limitations in the product, not only in the report


## The ten questions you will be asked

**"Why Streamlit?"**
Because the project needed a working application, not only a dashboard — one
that loads the actual trained models, runs predictions, accepts a file upload
and returns downloads. Streamlit does that in pure Python, so the app reuses
`src/data_loader.py` and `src/dashboard_utils.py` rather than reimplementing
the metrics.

**"Why not Flask?"**
Flask is a web framework, not a data-app framework. I would have had to write
routes, templates, HTML, JavaScript and a charting layer before showing a
single number. Streamlit gave me widgets, layout and Plotly integration out of
the box. Flask would be the right choice if I needed a REST API for other
systems to call — which is exactly what I would build for production serving.

**"Why not Django?"**
Django is heavier still — an ORM, an admin, a migrations system, an auth
framework. None of that is needed here: there is no user model, no
database-backed CRUD, no multi-tenant requirement. Using Django would have been
infrastructure without purpose.

**"How does Streamlit execute Python?"**
It re-runs the entire script top to bottom on every interaction. There is no
callback model — when a user moves a slider, the script executes again with the
new widget value. That is why caching matters: without it, every filter change
would reload the database and re-read the models from disk.

**"How are the models loaded?"**
Through a `@st.cache_resource` loader that reads each `.pkl` with joblib and
returns a per-model status. It loads seven artefacts — the K-Means model and
its scaler, the value model and preprocessor, the prediction model and
preprocessor, and the forecasting model. If one is missing, that feature
reports it and the rest of the app keeps working; the test suite verifies this
by deleting a model file and restoring it afterwards.

**"How does the app interact with processed data?"**
`src/data_loader.py` is database-first: it opens
`data/customer_revenue_intelligence.db`, executes the `pbi_*` view definitions
and reads from them. If the database is absent it falls back to the processed
CSV files and says which source it is using. Loads are wrapped in
`@st.cache_data` so a filter change does not re-read anything.

**"How does CSV upload work?"**
`st.file_uploader` accepts the file, the app validates its columns against the
expected schema, and if validation fails it names the missing columns rather
than throwing a traceback. A sample file is provided so the user can see the
expected format. This path is covered by the headless tests.

**"How are filters implemented?"**
Through a shared `sales_filters()` helper in `src/dashboard_utils.py` that
renders the controls and returns the filtered DataFrame, so every page filters
the same way and the filter state is consistent across the charts on a page.

**"How are the Plotly charts generated?"**
Through one helper that applies the project theme, the colour sequence, the
gridline treatment and the title rendering, then returns the figure to
`st.plotly_chart`. Centralising it is why twelve pages look like one system.

**"How would you deploy the application?"**
Streamlit Community Cloud for a demo, or a container behind a reverse proxy
with authentication for anything real, with the data and model artefacts
mounted or pulled from object storage. It is **not** deployed — it runs
locally. Deployment, along with scheduled refresh and monitoring, is future
scope, and I would not claim otherwise.

## Live demo sequence — three minutes in the app

1. **Home** — point at the status pill: the app knows what is loaded.
2. **Executive Overview** — the KPI row. Say ₹6.01 Cr and 23.35%.
3. **Revenue Intelligence** — change one filter and let them watch every chart
   respond.
4. **Customer Segmentation** — switch on the at-risk high-value filter; the
   52-customer list appears. This is the moment that lands.
5. **Sales Forecast** — switch the interval from 80% to 95% and say why the
   band widens.
6. **Data Explorer** — download a CSV, so they see the output is takeable.

## If a page is slow

The first load of each page builds its cache. Open the app and click through
every page **before** the examiner walks in; after that, navigation is
instant. Recorded load times are in
`outputs/tables/streamlit_page_load_times.csv`.
