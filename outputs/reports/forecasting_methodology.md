# Sales Forecasting & Time-Series Revenue Forecasting - Step 9

> **SYNTHETIC DATA - generated for academic demonstration only.** Forecasts describe the synthetic dataset from Step 2 (seed 42).

## 1. Objective

Forecast total monthly revenue for the next months from the historical sales series, with honest uncertainty, and show that the chosen model adds value over simple baselines.

## 2. Data source

`data/processed/customer_sales_cleaned.csv` (Step 3 cleaned order lines). Revenue = Sales on Delivered lines (the project-wide revenue rule; Returned/Cancelled lines carry no revenue).

| Check | Result | OK |
|---|---|---|
| Required columns present | Order_Date, Sales, Profit, Quantity, Customer_ID, Product_ID, Category, Region | True |
| Missing values in required columns | 0 | True |
| Invalid (unparseable) Order_Date | 0 | True |
| Duplicate Order_Line_ID | 0 | True |
| Fully duplicated rows | 0 | True |
| Delivered lines with Sales <= 0 | 0 | True |
| Delivered lines with Quantity <= 0 | 0 | True |
| Date range | 2023-01-01 to 2025-12-31 (1,096 days) | True |
| Calendar days with no order | 0 | True |
| Months with no Delivered sales | 0 | True |
| Orders per day (mean / min / max) | 12.1 / 2 / 37 | True |
| Delivered lines per month (min / max) | 203 / 911 | True |
| Lines by status | Delivered 16,860; Returned 1,101; Cancelled 709 | True |

## 3. Forecasting frequency

**Monthly.** Every one of the 1,096 days has orders, and all 36 months have Delivered sales, so monthly totals are complete. Monthly is the standard planning period, and 36 observations are enough for simple models and a backtest; weekly data would be noisier (about 12 orders a day), and quarterly would leave only 12 points.

## 4. Target variable

`Revenue` = sum of Delivered Sales (Rs) per calendar month, company total (`data/processed/monthly_sales_timeseries.csv`, which also holds profit, quantity, orders, active customers, AOV and margin).

## 5. Time period

2023-01 to 2025-12 (36 months). **Forecast horizon: 6 months** (2026-01 to 2026-06). Six months is the horizon that was actually evaluated on the validation, test and backtest windows; a 12-month horizon would extrapolate twice as far as anything tested, with only three seasonal cycles of history.

## 6. Data preparation

- Dates parsed and validated (no invalid or missing dates, no duplicate lines, no Delivered line with Sales <= 0).
- Aggregated to month starts; the monthly index was re-indexed to a complete calendar so that any gap would show as missing (NaN) rather than zero - there were none, so no filling was needed.
- Monthly totals reconcile with total Delivered sales (₹6.01 Cr).

## 7. Exploratory analysis

**Trend.** Revenue rose from an average of ₹10.88 L/month in the first 12 months to ₹22.69 L in the last 12 (linear trend +₹52,955 per month, R² 0.76). Annual growth: 51% (2024) and 38% (2025) - growth is positive but slowing.

| Year | Revenue | Mean_Month | Std_Month | CV_% | YoY_Growth_% | Q4_Share_% |
|---|---|---|---|---|---|---|
| 2023 | ₹1.31 Cr | ₹10.88 L | ₹3.85 L | 35.4 |  | 37.1 |
| 2024 | ₹1.98 Cr | ₹16.47 L | ₹4.66 L | 28.3 | 51.4 | 35.2 |
| 2025 | ₹2.72 Cr | ₹22.69 L | ₹4.25 L | 18.7 | 37.7 | 29.7 |

**Seasonality.** October was the highest month in all three years (seasonal index 1.70, 1.70, 1.37); November and December were also above average each year. Other months have no consistent pattern (e.g. February ranges 0.53-1.02). STL seasonal strength 0.68; Kruskal-Wallis test of the monthly index p = 0.017. With only three observations per calendar month, the evidence supports a **Q4 / October peak** but not a detailed month-by-month profile.

| Month_Number | 2023 | 2024 | 2025 | Mean_Index | Min_Index | Max_Index |
|---|---|---|---|---|---|---|
| 1 | 0.666 | 0.837 | 0.907 | 0.804 | 0.666 | 0.907 |
| 2 | 0.526 | 1.017 | 0.642 | 0.729 | 0.526 | 1.017 |
| 3 | 0.847 | 0.879 | 0.963 | 0.896 | 0.847 | 0.963 |
| 4 | 0.951 | 0.709 | 0.751 | 0.804 | 0.709 | 0.951 |
| 5 | 0.817 | 0.830 | 0.985 | 0.877 | 0.817 | 0.985 |
| 6 | 0.640 | 0.850 | 1.122 | 0.871 | 0.640 | 1.122 |
| 7 | 0.961 | 0.744 | 1.024 | 0.910 | 0.744 | 1.024 |
| 8 | 1.246 | 0.956 | 0.967 | 1.057 | 0.956 | 1.246 |
| 9 | 0.897 | 0.950 | 1.079 | 0.975 | 0.897 | 1.079 |
| 10 | 1.698 | 1.697 | 1.365 | 1.587 | 1.365 | 1.698 |
| 11 | 1.299 | 1.324 | 1.170 | 1.264 | 1.170 | 1.324 |
| 12 | 1.453 | 1.205 | 1.025 | 1.228 | 1.025 | 1.453 |

**Volatility.** Average absolute month-on-month change 24%. The 12-month rolling standard deviation rose with the level while the coefficient of variation fell (relative volatility declined). Months flagged by the STL residual (|z| >= 2):

| Month | Revenue | STL_Trend | STL_Seasonal | Residual_Z | Flag |
|---|---|---|---|---|---|
| 2024-02 | ₹16.76 L | ₹13.65 L | -₹4.44 L | 4.0 | unusually high |
| 2024-07 | ₹12.27 L | ₹16.45 L | -₹13,669 | -2.4 | unusually low |
| 2024-10 | ₹27.95 L | ₹17.64 L | ₹6.30 L | 2.0 | unusually high |

**Rolling statistics** (3- and 12-month windows; 12 months removes the seasonal cycle): the 12-month mean rises steadily (trend), the series is not stable in level, and absolute volatility is higher in 2024-2025 than in 2023.

## 8. Stationarity analysis

| Series | Observations | ADF_Statistic | p_value | Critical_5% | Conclusion |
|---|---|---|---|---|---|
| Revenue (level) | 36 | -2.213 | 0.201 | -2.949 | non-stationary (cannot reject unit root at 5%) |
| log(Revenue) | 36 | -2.246 | 0.190 | -2.951 | non-stationary (cannot reject unit root at 5%) |
| First difference | 35 | -3.531 | 0.007 | -2.992 | stationary (reject unit root at 5%) |
| Seasonal difference (lag 12) | 24 | -2.419 | 0.136 | -3.022 | non-stationary (cannot reject unit root at 5%) |

The level is non-stationary (p = 0.20); the log does not change that. The first difference is stationary (p = 0.007), so **d = 1** is used for ARIMA. A seasonal difference alone is not sufficient (it leaves only 24 points and does not pass). ETS and Theta handle trend internally, so no transformation is applied for them.

**ACF / PACF of the first difference** (approx. 95% bound +/-0.33): significant lags - ACF 1, 6, 12; PACF 1, 6. A negative lag-1 autocorrelation points to an MA(1) or AR(1) term; lag 12 is borderline, so seasonal variants were tested but kept minimal.

## 9. Baseline models

- **Naive:** every future month = the last observed month.
- **Seasonal naive:** every future month = the same month one year earlier.
Both use residual-based prediction intervals (random-walk formulas).

## 10. Advanced forecasting models

- **Exponential smoothing (ETS, statsmodels ETSModel)** - 6 configurations: SES (A,N,N), Holt (A,A,N), Damped Holt (A,Ad,N), Holt-Winters additive (A,A,A), Holt-Winters damped additive (A,Ad,A), Holt-Winters multiplicative (A,Ad,M). Parameters estimated by maximum likelihood; seasonal variants require two full years, which the 24-month training window just meets.
- **ARIMA / SARIMA (statsmodels ARIMA)** - 6 configurations chosen from the ADF/ACF/PACF evidence: ARIMA(0,1,1), ARIMA(1,1,0), ARIMA(0,1,1) + drift, ARIMA(1,1,1) + drift, SARIMA(0,0,0)(0,1,0)12 + drift, SARIMA(1,0,0)(0,1,0)12 + drift. (A first implementation using SARIMAX's `trend='t'` turned out to model a trend in the *differenced* series - a quadratic path - and was replaced; see the code comment.)
- **Theta method (optional model)** - simple exponential smoothing plus half the linear trend; its built-in seasonality test (lag-12 autocorrelation) decides whether to seasonally adjust first. Prophet is not installed and was not added (unnecessary dependency).

**Configuration choice inside each family** (fit on train, score on validation; lowest validation MAE):

| Family | Specification | MAE | RMSE | MAPE_% | WAPE_% | Bias_% | AIC | Best_in_Family |
|---|---|---|---|---|---|---|---|---|
| Naive | Naive (last month) | ₹3.15 L | ₹3.60 L | 16.4 | 15.5 | -2.2 |  | True |
| Seasonal naive | Seasonal naive (same month last year) | ₹6.97 L | ₹7.52 L | 32.8 | 34.3 | -30.7 |  | True |
| Exponential smoothing | SES (A,N,N) | ₹2.91 L | ₹3.61 L | 16.0 | 14.3 | 2.5 | 688.9 | False |
| Exponential smoothing | Holt (A,A,N) | ₹4.62 L | ₹5.48 L | 26.2 | 22.8 | 22.8 | 689.8 | False |
| Exponential smoothing | Damped Holt (A,Ad,N) | ₹2.75 L | ₹3.31 L | 15.2 | 13.5 | 2.2 | 687.8 | True |
| Exponential smoothing | Holt-Winters additive (A,A,A) | ₹3.46 L | ₹4.14 L | 17.2 | 17.0 | -7.7 | 714.5 | False |
| Exponential smoothing | Holt-Winters damped additive (A,Ad,A) | ₹4.32 L | ₹4.84 L | 20.9 | 21.3 | -13.8 | 719.8 | False |
| Exponential smoothing | Holt-Winters multiplicative (A,Ad,M) | ₹4.41 L | ₹5.40 L | 20.7 | 21.7 | -15.9 | 687.0 | False |
| ARIMA / SARIMA | ARIMA(0,1,1) | ₹2.91 L | ₹3.61 L | 16.0 | 14.3 | 2.5 | 659.8 | False |
| ARIMA / SARIMA | ARIMA(1,1,0) | ₹2.92 L | ₹3.54 L | 15.7 | 14.4 | 0.7 | 659.3 | False |
| ARIMA / SARIMA | ARIMA(0,1,1) + drift | ₹3.09 L | ₹4.16 L | 18.4 | 15.2 | 13.6 | 658.8 | False |
| ARIMA / SARIMA | ARIMA(1,1,1) + drift | ₹2.41 L | ₹3.41 L | 14.2 | 11.9 | 6.7 | 660.1 | True |
| ARIMA / SARIMA | SARIMA(0,0,0)(0,1,0)12 + drift | ₹3.32 L | ₹4.26 L | 17.6 | 16.4 | -3.2 | 358.5 | False |
| ARIMA / SARIMA | SARIMA(1,0,0)(0,1,0)12 + drift | ₹3.35 L | ₹4.26 L | 17.7 | 16.5 | -3.4 | 341.2 | False |
| Theta | Theta (seasonality auto-tested) | ₹2.63 L | ₹3.74 L | 15.6 | 12.9 | 8.5 |  | True |

AIC is shown for reference only; it is not comparable across differencing orders or model families.

## 11. Train / validation / test methodology

| Split | Start | End | Months | Revenue |
|---|---|---|---|---|
| Train | 2023-01 | 2024-12 | 24 | ₹3.28 Cr |
| Validation | 2025-01 | 2025-06 | 6 | ₹1.22 Cr |
| Test | 2025-07 | 2025-12 | 6 | ₹1.50 Cr |

Strictly chronological, no shuffling. Validation forecasts are fitted on train only; test forecasts are refitted on train + validation; the future forecast is refitted on all 36 months. No model ever sees the months it forecasts.

## 12. Backtesting

Two evaluation windows of 6 months are a small sample, so a **rolling-origin (expanding-window) backtest** was run: at each origin from 2024-12 to 2025-06 the model is fitted on all months up to the origin and forecasts the next 6 (7 folds). This checks whether a model is good in general or only on one window.

| Family | Folds | Mean_MAE | Mean_MAPE_pct | Std_MAPE_pct | Worst_MAPE_pct | Mean_Bias_pct | Folds_Won |
|---|---|---|---|---|---|---|---|
| Exponential smoothing | 7 | ₹2.99 L | 13.1 | 2.4 | 15.5 | -7.1 | 2 |
| ARIMA / SARIMA | 7 | ₹2.99 L | 13.5 | 3.6 | 17.8 | -3.8 | 4 |
| Theta | 7 | ₹3.29 L | 14.6 | 3.8 | 19.9 | -7.1 | 1 |
| Naive | 7 | ₹4.23 L | 18.5 | 9.4 | 32.7 | -11.6 | 0 |
| Seasonal naive | 7 | ₹7.64 L | 33.4 | 4.2 | 37.8 | -32.5 | 0 |

**Mean absolute % error by months ahead (all folds)**

| Family | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| ARIMA / SARIMA | 18.3 | 13.0 | 11.8 | 12.8 | 12.0 | 12.9 |
| Exponential smoothing | 15.2 | 14.0 | 11.1 | 13.9 | 12.6 | 11.9 |
| Naive | 21.7 | 16.0 | 15.9 | 17.4 | 18.6 | 21.2 |
| Seasonal naive | 34.9 | 34.2 | 37.2 | 33.8 | 31.8 | 28.4 |
| Theta | 17.1 | 15.2 | 12.3 | 16.1 | 13.0 | 13.7 |

Limitation: all folds lie in 2025, so the backtest covers one year of business conditions.

## 13. Evaluation metrics

- **MAE** - average absolute error in Rs per month. **RMSE** - penalises large misses more.
- **MAPE** - average absolute % error; safe here because no month has zero revenue.
- **sMAPE / WAPE** - symmetric % error and total absolute error / total actual (reported for robustness).
- **Bias** - (sum forecast - sum actual) / sum actual. **Interval coverage** - share of test months inside the 95% interval.

## 14. Model comparison

| Family | Specification | Val_MAE | Val_RMSE | Val_MAPE_% | Test_MAE | Test_RMSE | Test_MAPE_% | Test_sMAPE_% | Test_WAPE_% | Test_Bias_% | Test_95%_Interval_Coverage_% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Naive | Naive (last month) | ₹3.15 L | ₹3.60 L | 16.4 | ₹2.58 L | ₹3.02 L | 10.1 | 10.1 | 10.3 | 1.5 | 100.0 |
| Seasonal naive | Seasonal naive (same month last year) | ₹6.97 L | ₹7.52 L | 32.8 | ₹6.19 L | ₹6.83 L | 25.6 | 30.7 | 24.7 | -24.7 | 66.7 |
| Exponential smoothing | Damped Holt (A,Ad,N) | ₹2.75 L | ₹3.31 L | 15.2 | ₹2.73 L | ₹3.96 L | 9.8 | 10.8 | 10.9 | -10.9 | 83.3 |
| ARIMA / SARIMA | ARIMA(1,1,1) + drift | ₹2.41 L | ₹3.41 L | 14.2 | ₹2.61 L | ₹3.07 L | 10.5 | 10.1 | 10.4 | 4.7 | 100.0 |
| Theta | Theta (seasonality auto-tested) | ₹2.63 L | ₹3.74 L | 15.6 | ₹2.13 L | ₹3.11 L | 7.8 | 8.2 | 8.5 | -4.7 | 100.0 |

## 15. Final model selection

**Rule (fixed before modelling):** lowest mean backtest MAPE among models that beat **both** baselines on test MAE; within 5% of that MAPE the simpler family wins. If no model beat the baselines, the better baseline would be kept.

| Family | Specification | Mean_MAPE_pct | Std_MAPE_pct | Val_MAPE_% | Test_MAPE_% | Test_MAE | Beats_Both_Baselines_on_Test | Selected |
|---|---|---|---|---|---|---|---|---|
| Exponential smoothing | Damped Holt (A,Ad,N) | 13.1 | 2.4 | 15.2 | 9.8 | ₹2.73 L | False | False |
| ARIMA / SARIMA | ARIMA(1,1,1) + drift | 13.5 | 3.6 | 14.2 | 10.5 | ₹2.61 L | False | False |
| Theta | Theta (seasonality auto-tested) | 14.6 | 3.8 | 15.6 | 7.8 | ₹2.13 L | True | True |
| Naive | Naive (last month) | 18.5 | 9.4 | 16.4 | 10.1 | ₹2.58 L | True | False |
| Seasonal naive | Seasonal naive (same month last year) | 33.4 | 4.2 | 32.8 | 25.6 | ₹6.19 L | True | False |

**Selected: Theta - Theta (seasonality auto-tested).** Test MAE ₹2.13 L vs ₹2.58 L (naive) and ₹6.19 L (seasonal naive); test MAPE 7.8%, validation MAPE 15.6%, backtest mean MAPE 14.6% (naive 18.5%). Its seasonality test did not detect significant 12-month seasonality, so it forecasts level + trend only. Honest caveat: Exponential smoothing (13.1%) and ARIMA / SARIMA (13.5%) had a slightly lower backtest MAPE but did not beat the naive forecast on the test window, so the top models are close and the ranking could change with more data.

## 16. Future forecast

| Month | Forecast | Lower_80 | Upper_80 | Lower_95 | Upper_95 |
|---|---|---|---|---|---|
| 2026-01 | ₹25.67 L | ₹20.78 L | ₹30.56 L | ₹18.19 L | ₹33.14 L |
| 2026-02 | ₹25.93 L | ₹18.56 L | ₹33.30 L | ₹14.66 L | ₹37.20 L |
| 2026-03 | ₹26.20 L | ₹16.99 L | ₹35.40 L | ₹12.12 L | ₹40.27 L |
| 2026-04 | ₹26.46 L | ₹15.73 L | ₹37.19 L | ₹10.05 L | ₹42.87 L |
| 2026-05 | ₹26.73 L | ₹14.66 L | ₹38.79 L | ₹8.28 L | ₹45.18 L |
| 2026-06 | ₹26.99 L | ₹13.73 L | ₹40.26 L | ₹6.70 L | ₹47.28 L |

Total forecast 2026-01..2026-06: **₹1.58 Cr** (95% monthly intervals shown; they widen with the horizon). Model parameters: `{'b0': 52954.790920205916, 'alpha': 0.47718796597345875, 'seasonality_detected_by_theta_test': False}`.

**By business dimension.** Each category and region series (36 months) was tested the same way; a forecast is published only if its test MAPE <= 20% and it beats both baselines on test MAE.

| Dimension | Level | Monthly_Mean_Revenue | CV_% | Selected_Test_MAPE_% | Selected_Test_MAE | Naive_Test_MAE | Seasonal_Naive_Test_MAE | Naive_Test_MAPE_% | Published |
|---|---|---|---|---|---|---|---|---|---|
| Category | Beauty | ₹94,499 | 41.3 | 12.9 | ₹18,939 | ₹22,666 | ₹33,636 | 14.8 | True |
| Category | Books | ₹31,586 | 51.3 | 30.8 | ₹15,333 | ₹14,246 | ₹16,919 | 28.8 | False |
| Category | Electronics | ₹8.36 L | 41.9 | 10.3 | ₹1.41 L | ₹2.99 L | ₹3.24 L | 25.7 | True |
| Category | Fashion | ₹3.35 L | 41.2 | 13.9 | ₹73,104 | ₹98,164 | ₹1.58 L | 17.7 | True |
| Category | Home & Kitchen | ₹2.88 L | 36.1 | 14.3 | ₹50,090 | ₹51,054 | ₹86,410 | 13.9 | True |
| Category | Sports | ₹83,104 | 58.6 | 35.1 | ₹58,545 | ₹88,219 | ₹61,197 | 56.6 | False |
| Region | Central | ₹2.12 L | 47.3 | 20.6 | ₹70,416 | ₹70,484 | ₹82,616 | 22.3 | False |
| Region | East | ₹2.07 L | 50.0 | 25.1 | ₹98,885 | ₹1.12 L | ₹1.39 L | 28.6 | False |
| Region | North | ₹4.00 L | 42.3 | 22.1 | ₹1.12 L | ₹1.18 L | ₹1.01 L | 24.1 | False |
| Region | South | ₹4.51 L | 41.3 | 15.3 | ₹1.10 L | ₹92,283 | ₹1.90 L | 15.9 | False |
| Region | West | ₹3.99 L | 41.2 | 14.6 | ₹86,050 | ₹98,462 | ₹1.89 L | 17.0 | True |

The baseline comparison uses MAE, so a series can be published with a slightly higher MAPE than naive (its errors are smaller in rupee terms, e.g. in high-revenue months).

## 17. Business interpretation

| Area | Evidence | Planning interpretation |
|---|---|---|
| Revenue direction | Revenue grew 51% in 2024 and 38% in 2025; the 6-month forecast totals ₹1.58 Cr vs ₹1.22 Cr in the same months of 2025 (+30%). | Plan for continued growth, but the forecast is a model extrapolation of 3 years of history. |
| Seasonality | Highest month each year: 2023: month 10, 2024: month 10, 2025: month 10. Mean seasonal index for October 1.59 (range 1.37-1.70); Q4 share of annual revenue 2023: 37%, 2024: 35%, 2025: 30%. Kruskal-Wallis across months p = 0.017. | A recurring Q4/October peak is supported; other month-to-month differences are not consistent across years. |
| Volatility | Average absolute month-on-month change 24%; largest rise +89% (2023-10), largest fall -29% (2025-02). | Single-month targets need buffers; quarterly totals are more stable. |
| Forecast accuracy | Selected model: backtest mean MAPE 14.6% (7 folds), test MAPE 7.8%. | Expect monthly errors of roughly this size; use the intervals, not only the point forecast. |
| Uncertainty | The 95% interval is on average 111% of the point forecast wide. | Useful for cash-flow and inventory buffers: plan ranges, not single numbers. |
| Planning implications | Last 6 actual months ₹1.50 Cr vs previous 6 ₹1.22 Cr. | Inventory, staffing and marketing budgets can be phased to the forecast path and to the Q4 peak; specific actions are for the recommendation step. |

Forecasts are estimates under the assumption that the 2023-2025 pattern continues; they are not guarantees. The forecast window (January-June) does not include the October peak - a 12-month plan would need a seasonal model and more history to quantify Q4.

## 18. Limitations

1. **Synthetic data** generated in Step 2.
2. **Short history:** 36 months = 3 seasonal cycles; seasonal estimates rest on 3 values per month.
3. **Small evaluation windows:** 6 validation + 6 test months; backtest folds all fall in 2025.
4. **Close competition:** the three non-baseline models' backtest MAPEs span 13.1-14.6%.
5. **No seasonal term in the selected model** - acceptable for a January-June horizon, not for Q4.
6. **Univariate:** no promotions, prices, marketing or macro drivers; structural changes would not be anticipated.
7. **Wide intervals:** by month 6 the 95% interval spans ₹6.70 L-₹47.28 L around a forecast of ₹26.99 L (about +/-75%).
8. **Delivered revenue only;** returns/cancellations after month-end are not modelled.

## 19. Reproducibility instructions

```bash
python src/forecasting.py                       # full pipeline (~1 min), QC checklist printed
jupyter notebook notebooks/07_sales_forecasting.ipynb
```

```python
import joblib
a = joblib.load('models/forecasting_model.pkl')     # dict with the fitted statsmodels result
a['fitted_model'].forecast(6)                      # reproduces data/processed/revenue_forecast.csv (future rows)
```

All models are deterministic (maximum likelihood); the only simulation option (multiplicative ETS intervals) uses seed 42. statsmodels 0.15.0.

## Quality-control checklist

| Check | Evidence | Pass |
|---|---|---|
| Actual cleaned dataset used | data/processed/customer_sales_cleaned.csv | True |
| Correct date handling (all dates parsed; monthly index regular) | 36 months, freq=MS | True |
| Monthly aggregation reconciles with Delivered sales | ₹6.01 Cr vs ₹6.01 Cr | True |
| No missing months (none filled with zero) | 0 | True |
| No random split: train < validation < test in time | 2024-12 < 2025-01; 2025-06 < 2025-07 | True |
| No leakage: validation fits use train only; test fits use train+validation only; backtest fits use data before each origin | by construction (history slices) | True |
| Baselines implemented | Naive, Seasonal naive | True |
| Exponential smoothing tested | 6 configurations | True |
| ARIMA / SARIMA tested | 6 configurations | True |
| Stationarity checked (ADF) | level, log, first and seasonal differences | True |
| Backtesting performed | 7 expanding-window folds | True |
| MAE, RMSE, MAPE, sMAPE, WAPE calculated | no zero monthly actuals, so MAPE is defined | True |
| Final model selected by the pre-set rule | Theta: Theta (seasonality auto-tested) | True |
| Future forecast generated with intervals | 6 months | True |
| Forecast values finite and intervals ordered | lower <= forecast <= upper | True |
| Forecast table reconciles with actuals | 48 actual values | True |
| Model artefact saved and reproduces the future forecast after reload | models/forecasting_model.pkl | True |
| Metadata saved | models/forecasting_metadata.json | True |

## Output files

- `data/processed/monthly_sales_timeseries.csv`, `data/processed/revenue_forecast.csv`
- `models/forecasting_model.pkl`, `models/forecasting_metadata.json`
- `outputs/tables/forecast_*.csv` (incl. `forecast_model_comparison.csv`, `forecast_backtest_*.csv`)
- `outputs/figures/forecasting/` - historical_revenue_trend.png, monthly_revenue_pattern.png, rolling_mean_std.png, seasonal_pattern.png, revenue_distribution.png, acf_pacf.png, forecast_model_comparison.png, backtest_results.png, validation_test_forecasts.png, actual_vs_forecast.png, forecast_by_dimension.png, actual_vs_forecast_interactive.html
