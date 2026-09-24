# Last-Minute Revision — 5 Minutes

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

---

**PROJECT**
A customer revenue intelligence platform: retail transaction data → cleaning →
segmentation → value → prediction → forecasting → dashboard and application.

**PROBLEM**
Businesses report revenue in aggregate but take decisions at customer level.

**DATA**
Synthetic, seed 42. 18,819 raw → 18,670 clean
lines · 1,984 purchasing customers · 61 products ·
5 regions · 01 January 2023–31 December 2025 (36 months) ·
₹6.01 Cr delivered revenue.

**TOOLS**
Python (pandas, NumPy, scikit-learn 1.8.0, statsmodels 0.15.0, Plotly) · SQL
(SQLite) · Power BI (DAX) · Streamlit · Jupyter.

**METHOD**
Data → Cleaning → EDA → RFM → K-Means → CLV → Prediction → Forecasting → SQL →
Power BI + Streamlit → Recommendations.

**MODELS**
- K-Means, K = 4 (silhouette 0.3534)
- Random forest — forward customer value
- Linear regression — next-quarter revenue
- Theta: Theta (seasonality auto-tested) — monthly revenue forecast

**IMPORTANT METRICS**

| | |
|---|---|
| Revenue / margin | ₹6.01 Cr / 23.35% |
| Orders / AOV | 12,212 / ₹4,917.83 |
| Silhouette / ARI vs RFM | 0.3534 / 0.3952 |
| Value model R² / Spearman | 0.2705 / 0.4869 |
| Prediction R² / MAE | 0.0557 / ₹5,658 |
| Forecast backtest MAPE | 14.56% |
| Forecast total (80% interval) | ₹1.58 Cr (₹1.00 Cr–₹2.16 Cr) |
| SQL / DAX / app pages | 57 / 84 / 12 |
| Project audit | 135 checks, 134 pass |

**KEY FINDINGS**
1. Top 10% of customers = 45.39% of revenue; top 20% = 64.33%.
2. Champions 16.84% of customers, 53.83% of revenue.
3. RFM and K-Means find the same high-value group (ARI 0.3952).
4. 52 high-value customers inactive 180+ days (₹26.51 L).
5. Repeat customers 89.42% of base, 98.59% of revenue.
6. Electronics = 50.10% of revenue at 10.85%
   margin; Beauty earns 46.49%.
7. Zero discount = best margin in 6/6
   categories (association, not cause).
8. Company forecasting works; individual prediction does not.

**KEY BUSINESS VALUE**
A short, specific action list: protect the top decile, work the
52-customer inactive list, manage category mix, test the discount
relationship — with every figure agreeing across Python, SQL, DAX and the app.

**LIMITATIONS**
Synthetic data · 36-month history · weak individual prediction
(R² 0.0557) · univariate forecast · association not causation · no
churn label · Power BI pages are design mockups · no user testing · no
deployment or monitoring.

**FUTURE**
Real data · business-defined inactivity label · two-stage prediction · external
regressors · a controlled discount experiment · scheduled runs with drift
monitoring · complete the `.pbix` on Windows.

---

### Three sentences to have word-perfect

1. "The dataset is synthetic, generated with a fixed seed for academic
   demonstration — it describes no real company."
2. "Power BI Desktop is Windows-only and wasn't available, so those pages are
   design mockups rendered from the real data, not screenshots."
3. "Customer-level prediction is weak at R² 0.0557, and I report it as
   weak — 53.0% of customer-quarters have no order at all."

### If you don't know

"That value was not directly measured in this project."
"It was considered as a possible extension, but it was not part of the
implemented pipeline."
