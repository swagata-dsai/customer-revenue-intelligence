# "Why Did You Use This?" — Live Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

Every answer starts with *because* and names something specific in the project.

**Why Python?**
Because the whole pipeline — cleaning, statistics, clustering, regression,
time series and the application — exists in one ecosystem, so nothing has to be
handed between languages. It also let the Streamlit app reuse the pipeline's
own modules rather than reimplementing the metrics, which is why a number on
screen cannot drift from the report.

**Why Pandas?**
Because the unit of work is a labelled table with mixed types, and pandas gives
vectorised group-by, join, reshape and time handling on exactly that. At
18,670 rows and 51 columns the data fits comfortably
in memory, so a DataFrame is the right structure rather than a database round
trip for every operation.

**Why NumPy?**
Because it is the numerical layer under pandas and scikit-learn, and I used it
directly for the transforms — `log1p` on the skewed RFM features before
clustering, and `arcsinh` on the skewed customer-value features.

**Why SQL?**
Because I wanted a second, independent implementation. The same definitions
written in a different language means that when SQL and Python agree on
₹6.01 Cr and 23.35%, that is evidence rather than a copy of one
code path. It also normalises the data properly — 11 tables with
enforced keys — instead of one flat file.

**Why RFM?**
Because it is auditable. A business user can see exactly why a customer landed
in a segment, which a clustering cannot offer. And recency, frequency and
monetary value carry most of the information needed to rank a customer base,
which is why it has survived since Hughes formalised it in 1994.

**Why K-Means?**
Because it is an independent check on my own rules. RFM imposes boundaries I
chose; K-Means finds whatever grouping is actually in the data. Their agreement
on the high-value group — ARI 0.3952 — is stronger evidence than either
method alone.

**Why StandardScaler?**
Because K-Means uses Euclidean distance and monetary value runs to lakhs while
frequency is a count under 50. Without scaling, monetary value would determine
every cluster by itself. It sits after `log1p` in a persisted pipeline, so the
same transformation is applied at scoring time.

**Why PCA?**
Because I needed to show four clusters in three dimensions on a two-dimensional
slide, and PC1 plus PC2 explain 95.09% of the variance — so the
picture is faithful. It was used for **visualisation only**; reducing three
features before clustering would have added an unexplained transformation for
no benefit.

**Why CLV?**
Because past spend and future worth are different questions, and treating them
as one misdirects effort. Separating measured historical value from estimated
forward value is what produces the actionable output: the 52
high-value customers who have gone quiet.

**Why machine learning at all?**
Because two of the questions cannot be answered by aggregation. Finding
behavioural groups without imposing rules needs unsupervised learning, and
estimating next-quarter revenue from a customer's history needs a fitted model.
Where aggregation was sufficient — the KPIs, the concentration curve — I used
aggregation.

**Why time-based validation?**
Because the task is predicting the future from the past, and a random split
would train on quarters that come after the test quarters. That inflates the
score and means nothing in practice. Everything time-dependent here uses a
chronological split, and the forecast additionally uses rolling-origin
backtesting over 7 folds.

**Why Power BI?**
Because a business audience needs governed self-service, not a notebook. A star
schema with 84 conformed measures lets a manager slice revenue
by date, region, category or segment without an analyst and without any risk of
computing revenue a different way.

**Why Streamlit?**
Because the project needed a working application, not only a dashboard. Power
BI cannot load a scikit-learn model or a statsmodels object; any page that
needs a live model — prediction, forecasting — has to run Python, and Streamlit
does that while reusing the pipeline's own modules.

**Why Plotly?**
Because the application needed interactivity — hover, zoom, legend toggling —
that a static image cannot give, and it integrates directly with Streamlit.
Matplotlib is used for the report and notebook figures, where print quality
matters more than interaction.

**Why forecasting as well as prediction?**
Because they answer different planning questions. Prediction tells you about a
customer; forecasting tells you about the company. And the contrast turned out
to be a finding in itself: company revenue forecasts to 14.56%
backtest MAPE while individual revenue predicts at R² 0.0557.

**Why synthetic data?**
Because it removes any confidentiality constraint while preserving the full
analytical problem, and it gives something real data cannot: a known ground
truth. The generator logs every defect it injects, so the cleaning stage can be
audited against what was actually done to the data. The cost — which I state
everywhere — is that the numbers describe no real business.
