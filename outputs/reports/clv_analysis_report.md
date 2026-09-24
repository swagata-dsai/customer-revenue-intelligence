# Customer Lifetime Value (CLV) Analysis - Step 7

> **SYNTHETIC DATA - generated for academic demonstration only.** All numbers come from the synthetic dataset generated in Step 2 (seed 42) and cleaned in Step 3. They illustrate the method; they are not facts about a real company.

Reproduce: `python src/clv.py` (about 20 seconds). Notebook: `notebooks/05_customer_lifetime_value.ipynb`.

## 1. Objective

Measure what each customer has been worth, estimate what each customer may be worth over the next 12 months, and compare both views across the Step 5 RFM segments and Step 6 K-Means clusters. Two quantities are kept strictly apart:

| | Observed historical value | Estimated future value |
|---|---|---|
| What it is | Delivered revenue / profit actually generated, 2023-01-01 to 2025-12-31 | Model estimate of Delivered profit in the next 12 months |
| Nature | Fact (reconciles to the transactions) | Estimate under stated assumptions |
| Columns | `Historical_Revenue_CLV`, `Historical_Profit_CLV` | `Estimated_12M_Future_Profit`, `Illustrative_3Y_Value` |

## 2. CLV definition

Customer Lifetime Value is the economic value a customer is expected to generate over the relevant customer relationship period. There are three broad ways to measure it:

1. **Historical CLV** - total value already generated (revenue, or better, profit = revenue - cost).
2. **Simplified predictive CLV** - Expected value = Average Order Value x expected purchase frequency x expected margin x expected lifetime.
3. **Probabilistic / ML CLV** - statistical models of purchasing (BG/NBD + Gamma-Gamma) or supervised models trained on past behaviour -> later value.

This project implements (1) in full, tests (2) and (3) against a real hold-out year, and uses the best-supported approach for the estimate.

## 3. Historical value methodology

- Revenue, cost and profit use **Delivered lines only** (project rule since Step 3). Returned and Cancelled lines carry zero revenue and profit and are counted separately.
- `Historical_Revenue_CLV` = sum of Sales; `Historical_Profit_CLV` = sum of Profit (= Sales - Cost). Profit CLV is the economically meaningful measure; revenue CLV is kept for comparison.
- Tenure = reference date (2026-01-01) - first delivered purchase. For 38.7% of customers ('Existing before 2023') the true first purchase is before the data starts, so tenure and historical value are **minimums** (left-censored).

**Aggregate results**

| Measure | Customers | Total | Mean | Median | Std | Min | Max | Mean_to_Median | Skewness | Customers_below_zero |
|---|---|---|---|---|---|---|---|---|---|---|
| Historical revenue | 1984 | ₹6.01 Cr | ₹30,270 | ₹13,513 | ₹43,790 | ₹238 | ₹4.18 L | 2.24 | 3.21 | 0 |
| Historical profit | 1984 | ₹1.40 Cr | ₹7,068 | ₹3,893 | ₹8,863 | -₹5,258 | ₹67,798 | 1.82 | 2.61 | 32 |

Historical profit margin: 23.3%. Revenue and profit are both strongly right-skewed (skewness 3.21 and 2.61); the mean is 1.82x the median for profit, so medians and percentiles are reported alongside means.

**Concentration**

| Top_Customers_% | Customers | Revenue_Share_% | Profit_Share_% |
|---|---|---|---|
| Top 1% | 20 | 9.0% | 7.1% |
| Top 5% | 99 | 29.9% | 26.4% |
| Top 10% | 198 | 45.4% | 41.0% |
| Top 20% | 397 | 64.3% | 59.3% |
| Top 50% | 992 | 90.0% | 87.5% |

Gini coefficient: revenue 0.61, profit 0.56.

**Percentiles**

| Percentile | Historical_Revenue | Historical_Profit | Total_Orders | Customer_Tenure_Days |
|---|---|---|---|---|
| P1 | ₹648 | -₹609 | 1 | 27 |
| P5 | ₹1,649 | ₹450 | 1 | 84 |
| P10 | ₹2,632 | ₹792 | 1 | 152 |
| P25 | ₹5,790 | ₹1,755 | 3 | 457 |
| P50 | ₹13,513 | ₹3,893 | 4 | 788 |
| P75 | ₹35,787 | ₹8,923 | 8 | 967 |
| P90 | ₹75,003 | ₹16,107 | 12 | 1058 |
| P95 | ₹1.18 L | ₹28,165 | 19 | 1078 |
| P99 | ₹2.29 L | ₹43,001 | 27 | 1093 |

**Single-purchase customers (investigated separately)**

| Is_Single_Purchase | Customers | Customer_Share_% | Median_Profit | Avg_Profit | Profit_Share_% | Median_Days_Since_Purchase |
|---|---|---|---|---|---|---|
| Repeat purchasers | 1774 | 89.4% | ₹4,590 | ₹7,792 | 98.6% | 112 |
| Single purchase | 210 | 10.6% | ₹735 | ₹952 | 1.4% | 202 |

Single-purchase customers have no repeat interval, so a purchase rate cannot be estimated for them from their own history; the predictive model uses cross-customer patterns instead.

## 4. Can the data support predictive CLV?

| Requirement | Evidence | Supported |
|---|---|---|
| Repeat purchasing | 89.4% of customers have 2+ delivered orders | Yes |
| Purchase frequency | median 4 orders per customer (P90 12) | Yes |
| Time period | 2023-01-01 to 2025-12-31 (36 months) - enough for a 12-month feature window + 12-month target, twice | Yes |
| Customer tenure | measurable from first observed purchase; LEFT-CENSORED for 38.7% of customers ('Existing before 2023') | Partly |
| Churn / inactivity | no churn flag in the data; of customers inactive >= 180 days, 41% (cutoff 2024-01-01), 56% (cutoff 2025-01-01) bought again within 12 months | No - churn cannot be observed |
| Stationarity | active customers per year 2023: 1,137 / 2024: 1,328 / 2025: 1,716; orders 2023: 2,811 / 2024: 4,014 / 2025: 5,387 | No - activity grows year on year |
| Customer-level history | 12,212 delivered orders for 1,984 customers | Yes |

**Inactivity is not churn.** The data has no churn flag, so an inactivity threshold was tested against what customers actually did next (two real cutoffs):

| Cutoff | Threshold_Days | Customers_Inactive_>=_Threshold | Bought_Again_Next_12M_% | Bought_Again_if_Below_Threshold_% |
|---|---|---|---|---|
| 2024-01-01 | 30 | 884 | 68.6% | 88.5% |
| 2024-01-01 | 60 | 658 | 64.7% | 84.3% |
| 2024-01-01 | 90 | 474 | 58.6% | 83.3% |
| 2024-01-01 | 180 | 244 | 41.0% | 81.7% |
| 2024-01-01 | 270 | 108 | 36.1% | 76.9% |
| 2025-01-01 | 30 | 1264 | 79.2% | 98.7% |
| 2025-01-01 | 60 | 1014 | 74.3% | 98.9% |
| 2025-01-01 | 90 | 770 | 67.4% | 98.0% |
| 2025-01-01 | 180 | 558 | 56.5% | 97.7% |
| 2025-01-01 | 270 | 417 | 50.1% | 95.1% |
| 2025-01-01 | 365 | 308 | 41.9% | 93.3% |

Time between repeat orders: median 54 days, P75 123, P90 232. A **180-day** threshold sits between P75 and P90 of normal repeat gaps, and beyond it the chance of buying again falls clearly (e.g. 41% vs 82% at 2024-01-01, 56% vs 98% at 2025-01-01). Because 41-56% of such customers still bought again, they are called **potentially at-risk**, never churned.

**Probabilistic model check (BG/NBD + Gamma-Gamma)**

BG/NBD was implemented with scipy (no extra package), fitted on 2023-2024 and tested on 2025:

| Item | Result |
|---|---|
| Calibration period | 2023-01-01 to 2024-12-31 |
| Hold-out period | 2025-01-01 to 2025-12-31 |
| Customers in calibration | 1,635 |
| Fitted parameters (r, alpha, a, b) | 1.866, 32.10, 0.0817, 0.854 |
| Optimiser converged | True |
| Hold-out orders: predicted vs actual | 4,022 vs 4,575 (87.9% of actual) |
| Hold-out orders per customer: MAE | 1.54 |
| Hold-out orders per customer: R² | 0.381 |
| Hold-out orders: Spearman rank correlation | 0.611 |
| Gamma-Gamma check: Pearson r(frequency, avg order value), repeat customers | 0.225 (p = 1.2e-16, n = 1,321) |
| Gamma-Gamma check: Spearman rho | 0.394 (p = 2.3e-50) |
| Gamma-Gamma usable? | No - absolute correlation > 0.1: frequency and spend are NOT independent |

BG/NBD captures repeat-purchase behaviour reasonably (88% of hold-out orders, R² 0.38 on order counts). **Gamma-Gamma was not used**: it requires spend per order to be independent of purchase frequency, and here they are positively correlated. BG/NBD also assumes a stable purchase process and a known start of each relationship; activity grew year on year and tenure is left-censored for many customers. BG/NBD is therefore kept as a **benchmark** in the model comparison, not as the final method.

## 5. Predictive methodology (time-based, no leakage)

| Panel | Feature period | Prediction (target) period | Customers | Role |
|---|---|---|---|---|
| Train | 2023-01-01 to 2023-12-31 | 2024-01-01 to 2024-12-31 | 1,137 | model fitting + 5-fold CV selection |
| Test | 2024-01-01 to 2024-12-31 | 2025-01-01 to 2025-12-31 | 1,328 | out-of-time evaluation only |
| Scoring | 2025-01-01 to 2025-12-31 | next 12 months after 2026-01-01 (not in the data) | 1,716 | estimate |

- **Target definition:** `Future_Profit_12M` = Delivered profit (₹) in the 12 months after the cutoff (0 if the customer did not buy).
- **Population:** customers with >= 1 Delivered order in the 12 months before the cutoff. The 268 customers with no order in 2025 are outside this population and receive the observed average next-year profit of the equivalent group at the 2025 cutoff: ₹830 (41% of that group bought again; n = 307).
- Features only use transactions dated **before** the cutoff; the target only uses transactions **on or after** it. RFM segments and cluster labels (computed on the full period) are **not** features.

## 6. Feature engineering

Thirteen candidate features were computed per customer on the 12-month window. Selection was done on the training panel only:

| Feature | Decision | Reason | VIF_All_Candidates | VIF_Final_Set | Spearman_with_Target_(train) |
|---|---|---|---|---|---|
| Recency_Days | Kept | value component (always kept) | 2.2 | 2.14 | -0.33 |
| Frequency | Kept | value component (always kept) | 416.4 | 3.52 | 0.36 |
| Revenue | Excluded | exact identity = AOV x Frequency | 1,590.4 |  | 0.32 |
| Profit | Excluded | exact identity = AOV x Frequency x Profit_Margin | 250.7 |  | 0.34 |
| Quantity | Excluded | VIF 7.3 > 5 (redundant with other features) | 7.4 |  | 0.34 |
| AOV | Kept | value component (always kept) | 824.9 | 2.36 | 0.19 |
| Avg_Profit_per_Order | Excluded | exact identity = AOV x Profit_Margin | 226.3 |  | 0.21 |
| Profit_Margin | Kept | value component (always kept) | 4.9 | 2.01 | -0.06 |
| Avg_Discount | Kept | VIF <= 5 | 3.7 | 2.38 | -0.13 |
| Categories | Kept | VIF <= 5 | 1.7 | 1.49 | 0.34 |
| Tenure_Days_Capped | Kept | VIF <= 5 | 4.0 | 3.39 | 0.05 |
| Purchase_Rate | Excluded | VIF 5.2 > 5 (redundant with other features) | 5.3 |  | 0.30 |
| Return_Rate | Kept | VIF <= 5 | 1.0 | 1.00 | 0.14 |

Revenue, Profit and profit per order are exact products of AOV, Frequency and margin; keeping them made the linear coefficients explode in opposite directions. Skewed features (Recency_Days, Frequency, AOV) enter on the arcsinh scale (like log, but defined for zero/negative values), then everything is standardised (`models/clv_preprocessor.pkl`).

## 7. Model selection

An interpretable baseline (Ridge regression, alpha chosen by internal CV) was compared with two non-linear models. **Selection rule:** lowest mean 5-fold CV RMSE on the training panel; the test year played no part in the choice.

| Model | CV_RMSE | CV_RMSE_Std | CV_MAE | CV_R2 | Selected |
|---|---|---|---|---|---|
| Ridge regression (baseline) | 3,793 | 341 | 2,538 | 0.191 | False |
| Random forest | 3,697 | 254 | 2,414 | 0.224 | True |
| Gradient boosting | 3,766 | 270 | 2,451 | 0.190 | False |

Selected: **Random forest**. For scoring, the same specification was refit on the train and test panels together (2,465 rows) so that the most recent year is used; its validation evidence is the out-of-time test below.

## 8. Model validation (out-of-time, 2025)

| Model | Type | MAE | RMSE | R2 | WAPE_% | Spearman | Top20_Capture_% | Predicted_to_Actual_Total |
|---|---|---|---|---|---|---|---|---|
| Ridge regression (baseline) | ML model | ₹2,853 | ₹4,469 | 0.201 | 69.5% | 0.478 | 41.7% | 0.80 |
| Random forest | ML model | ₹2,793 | ₹4,269 | 0.270 | 68.1% | 0.487 | 41.5% | 0.90 |
| Gradient boosting | ML model | ₹2,982 | ₹4,323 | 0.252 | 72.7% | 0.496 | 43.0% | 1.09 |
| Naive: last-12-month profit repeats | Benchmark | ₹2,947 | ₹4,648 | 0.135 | 71.8% | 0.440 | 41.1% | 0.85 |
| Simplified formula (AOV x F x margin x P(repeat)) | Benchmark | ₹2,859 | ₹4,606 | 0.151 | 69.7% | 0.464 | 40.7% | 0.68 |
| BG/NBD orders x avg profit per order | Benchmark | ₹2,693 | ₹4,356 | 0.241 | 65.7% | 0.490 | 41.7% | 0.75 |

- Selected model: R² **0.270**, MAE **₹2,793**, RMSE **₹4,269**, WAPE 68.1%, Spearman 0.487.
- **MAPE is not a headline metric:** 6.7% of test customers had zero future profit (MAPE undefined). On non-zero actuals only it is 176%, inflated by small actual values; WAPE (total absolute error / total actual) is reported instead.
- Ranking: the top 20% of customers by predicted value captured 41.5% of actual 2025 profit.
- Bias: predicted total = 90% of actual. Activity grew in 2025, which a model trained on 2023->2024 could not anticipate, so estimates are conservative in a growing year.
- Every method, including the benchmarks, explains a modest share of the variance (best R² 0.27: Random forest; lowest MAE ₹2,693: BG/NBD orders x avg profit per order). Individual next-year profit is noisy; the estimates are best used to **rank** customers.

**Calibration by predicted decile (test year)**

| Predicted_Decile | Customers | Mean_Predicted | Mean_Actual | Share_Purchased |
|---|---|---|---|---|
| 1 | 133 | ₹540 | ₹1,703 | 77% |
| 2 | 133 | ₹1,130 | ₹1,884 | 84% |
| 3 | 133 | ₹1,678 | ₹2,326 | 86% |
| 4 | 132 | ₹2,255 | ₹2,597 | 93% |
| 5 | 133 | ₹2,826 | ₹3,063 | 97% |
| 6 | 133 | ₹3,397 | ₹3,404 | 99% |
| 7 | 132 | ₹4,005 | ₹3,941 | 97% |
| 8 | 133 | ₹4,616 | ₹4,858 | 98% |
| 9 | 133 | ₹6,120 | ₹5,710 | 100% |
| 10 | 133 | ₹9,925 | ₹11,090 | 100% |

**Feature importance** (permutation on the test year; association, not causation)

| Feature | Permutation_MAE_Increase | Permutation_Std | Ridge_Std_Coefficient |
|---|---|---|---|
| Frequency | ₹628 | ₹41 | 1,149 |
| Avg_Discount | ₹100 | ₹17 | -277 |
| Recency_Days | ₹97 | ₹16 | -565 |
| AOV | ₹43 | ₹10 | 453 |
| Tenure_Days_Capped | ₹15 | ₹6 | -221 |
| Categories | ₹4 | ₹5 | 377 |
| Return_Rate | ₹1 | ₹3 | 188 |
| Profit_Margin | -₹1 | ₹9 | 334 |

The permutation column shows how much worse the selected model gets when a feature is scrambled; the Ridge column shows direction (₹ per +1 standard deviation, other features fixed). These describe patterns in this data; they do not show that changing a feature would change a customer's value.

**Illustrative multi-year value (not validated)**

`Illustrative_3Y_Value` = estimated 12-month profit x (1 + r + r²), r = observed annual repeat rate (0.839 pooled). No discounting is applied because no cost of capital is known for the company. Sensitivity:

| Scenario | Annual_Repeat_Rate | Horizon_Factor | Total_Illustrative_3Y_Value |
|---|---|---|---|
| 2023->2024 observed | 0.730 | 2.26 | ₹1.67 Cr |
| Pooled observed (used) | 0.839 | 2.54 | ₹1.88 Cr |
| 2024->2025 observed | 0.933 | 2.80 | ₹2.07 Cr |

There is no data after 2025 to test this figure; use it only to show scale and sensitivity.

## 9. CLV by RFM segment

| RFM_Segment | Customer_Count | Avg_Historical_Revenue | Avg_Historical_Profit_CLV | Historical_Profit_Share_% | Avg_Historical_Annual_Profit_Rate | Avg_Estimated_12M_Value | Total_Estimated_12M_Value | Est_12M_to_Historical_Annual_Rate | Avg_AOV | Avg_Frequency | Avg_Recency_Days |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Champions | 334 | ₹96,797 | ₹21,316 | 50.8% | ₹8,650 | ₹8,442 | ₹28.19 L | 0.98x | ₹6,103 | 15.4 | 33 |
| Loyal Customers | 240 | ₹35,745 | ₹8,401 | 14.4% | ₹4,317 | ₹4,550 | ₹10.92 L | 1.05x | ₹5,560 | 7.2 | 91 |
| Potential Loyalists | 152 | ₹14,418 | ₹3,655 | 4.0% | ₹2,280 | ₹3,365 | ₹5.12 L | 1.48x | ₹4,401 | 4.2 | 47 |
| Recent Customers | 91 | ₹5,369 | ₹1,863 | 1.2% | ₹1,710 | ₹3,069 | ₹2.79 L | 1.79x | ₹2,753 | 2.2 | 18 |
| Promising | 110 | ₹5,117 | ₹1,761 | 1.4% | ₹1,476 | ₹2,356 | ₹2.59 L | 1.60x | ₹2,511 | 2.2 | 59 |
| Needs Attention | 123 | ₹12,633 | ₹3,704 | 3.2% | ₹2,315 | ₹3,117 | ₹3.83 L | 1.35x | ₹3,210 | 4.5 | 121 |
| About to Sleep | 143 | ₹4,233 | ₹1,295 | 1.3% | ₹993 | ₹2,016 | ₹2.88 L | 2.03x | ₹2,250 | 2.1 | 115 |
| Can't Lose Them | 79 | ₹54,244 | ₹11,046 | 6.2% | ₹5,411 | ₹3,871 | ₹3.06 L | 0.72x | ₹5,882 | 9.8 | 228 |
| At Risk | 263 | ₹25,717 | ₹6,157 | 11.5% | ₹3,334 | ₹3,114 | ₹8.19 L | 0.93x | ₹5,202 | 5.9 | 259 |
| Hibernating | 148 | ₹6,593 | ₹2,270 | 2.4% | ₹1,427 | ₹2,292 | ₹3.39 L | 1.61x | ₹2,414 | 3.1 | 199 |
| Lost | 301 | ₹5,717 | ₹1,658 | 3.6% | ₹782 | ₹998 | ₹3.00 L | 1.28x | ₹2,939 | 2.1 | 732 |

`Est_12M_to_Historical_Annual_Rate` compares the estimate with each group's own historical annual profit rate (profit / tenure in years, tenure floored at 12 months). Below 1 = the model expects the group to slow down; above 1 = to grow (partly shrinkage toward the average for low-value groups).

## 10. CLV by ML cluster

| Cluster_ID | Cluster_Label | Customer_Count | Customer_% | Avg_Historical_Profit_CLV | Historical_Profit_Share_% | Avg_Historical_Annual_Profit_Rate | Avg_Estimated_12M_Value | Estimated_12M_Value_Share_% | Est_12M_to_Historical_Annual_Rate | Avg_AOV | Avg_Frequency | Avg_Recency_Days |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | High-Value, Active | 364 | 18.3% | ₹20,360 | 52.9% | ₹8,223 | ₹8,128 | 40.0% | 0.99x | ₹5,916 | 14.9 | 32 |
| 1 | Low-Value, Active | 453 | 22.8% | ₹2,107 | 6.8% | ₹1,565 | ₹2,621 | 16.1% | 1.68x | ₹2,637 | 2.8 | 64 |
| 2 | Mid-Value, Lapsing | 753 | 38.0% | ₹6,624 | 35.6% | ₹3,588 | ₹3,621 | 36.9% | 1.01x | ₹4,966 | 6.2 | 173 |
| 3 | Low-Value, Inactive | 414 | 20.9% | ₹1,617 | 4.8% | ₹878 | ₹1,267 | 7.1% | 1.44x | ₹3,073 | 2.1 | 591 |

## 11. High-value customer analysis

| Group | Definition | Customers | Customer_% | Historical_Profit_Share_% | Estimated_12M_Share_% | Median_Recency_Days | Top_RFM_Segments |
|---|---|---|---|---|---|---|---|
| High historical value | Historical profit CLV >= P80 (₹10,469) | 397 | 20.0% | 59.3% | 41.4% | 39 | Champions 72%; Loyal Customers 12%; Can't Lose Them 11% |
| High estimated future value | Estimated 12-month profit >= P80 (₹5,063) | 397 | 20.0% | 52.3% | 46.3% | 36 | Champions 66%; Loyal Customers 17%; At Risk 7% |
| High value + high engagement | High historical value AND F_Score >= 4 AND R_Score >= 4 (Step 5 scores) | 300 | 15.1% | 49.0% | 35.1% | 29 | Champions 95%; Loyal Customers 5% |
| Potentially at-risk high-value | High historical value AND no purchase for >= 180 days (not 'churned') | 52 | 2.6% | 5.1% | 2.9% | 228 | Can't Lose Them 67%; At Risk 33% |
| Future value opportunity | High estimated future value but NOT high historical value | 119 | 6.0% | 6.1% | 10.8% | 69 | Loyal Customers 39%; Champions 22%; At Risk 18% |

Customer-level flags are in `data/processed/customer_clv.csv` (Customer_ID only; no names).

## 12. Business interpretation

| Insight Area | Observation | Evidence | Business Interpretation |
|---|---|---|---|
| High-Value Customers | Top 20% of customers generated 59.3% of historical profit | 397 customers; Gini (profit) 0.56; mean/median profit ratio 1.82; skewness 2.61 | Customer value is concentrated: averages overstate the typical customer, so medians and percentiles are reported alongside means. |
| High-Value Customers | 52 high-value customers have not bought for >= 180 days | They hold 5.1% of historical profit; median recency 228 days | Potentially at-risk, not churned: at the 2025 cutoff 56% of customers inactive >= 180 days bought again within 12 months. |
| RFM Segments | Champions have the highest average estimated 12-month value (₹8,442), close to their historical annual rate (₹8,650) | 334 customers = 50.8% of historical profit and 38.1% of estimated 12-month value | The segment that generated most past value is also estimated to generate the most near-term value. Its share is lower on the estimate partly because the model pulls extreme customers toward the average (test top decile: predicted ₹9,925 vs actual ₹11,090). |
| RFM Segments | Can't Lose Them: estimated 12-month value is 0.72x their historical annual profit rate - the lowest ratio of any segment | 79 customers; average historical profit ₹11,046; estimated ₹3,871 vs annual rate ₹5,411; average recency 228 days | Historical value alone would overstate what this group is estimated to contribute next year. |
| ML Clusters | Clusters 0 and 2 hold 76.9% of estimated 12-month value | Cluster 0 (High-Value, Active): 18.3% of customers, 52.9% of historical profit, 40.0% of estimated value; Cluster 2 (Mid-Value, Lapsing): 38.0% of customers, 35.6% of historical profit, 36.9% of estimated value | Cluster 0 has by far the highest value per customer (₹8,128 estimated); the lapsing mid-value cluster matters because of its size. |
| ML Clusters | Cluster 1 (Low-Value, Active) has the highest estimated-to-historical ratio (1.68x) | Average estimated 12-month value ₹2,621 vs historical annual rate ₹1,565; average tenure 14 months | Recently active, low-value customers are estimated to be worth more next year than their short history shows - partly model shrinkage toward the average, so treat as a ranking signal, not a forecast. |
| Customer Tenure | Longer-tenure customers have higher historical profit (Spearman 0.36) | Median profit: tenure < 1 year ₹1,677, 1-2 years ₹4,068, >= 2 years ₹5,564; 38.7% of customers have left-censored tenure | Part of this is exposure (more time to buy), so tenure is not by itself evidence of loyalty. |
| Customer Tenure | 210 single-purchase customers (10.6%) hold 1.4% of profit | Median profit ₹735 vs ₹4,590 for repeat purchasers | Most value comes from repeat purchasing; a second purchase is the key step. |
| Profitability | Historical profit margin 23.3% overall | Historical profit ₹1.40 Cr on revenue ₹6.01 Cr; 32 customers have negative total profit | Profit CLV is the more economically meaningful measure; revenue CLV is kept for comparison. |
| Future Value | Out-of-time test (2024 features -> 2025 profit): R² 0.27, MAE ₹2,793 | Top 20% predicted captured 41.5% of actual 2025 profit; predicted/actual total 0.90; Spearman 0.49 | Useful for ranking customers by expected value; individual rupee estimates are approximate and totals are conservative when activity grows. |

**The eight Step 7 questions**

- **What is the current/historical value of each customer?** Stored per customer in customer_value_history.csv. Across 1,984 customers: historical revenue ₹6.01 Cr, historical profit ₹1.40 Cr; median profit per customer ₹3,893 vs mean ₹7,068.
- **Which customers generate the highest value?** The top 20% of customers by historical profit (397) generated 59.3% of all profit; the top 10% generated 41.0%. By RFM segment the top 20% are: Champions 72%; Loyal Customers 12%; Can't Lose Them 11%.
- **How does customer value differ across ML clusters?** Average historical profit ranges from ₹1,617 (Cluster 3: Low-Value, Inactive) to ₹20,360 (Cluster 0: High-Value, Active), which holds 52.9% of historical profit and 40.0% of estimated 12-month value.
- **How does customer value differ across RFM segments?** Highest average historical profit: Champions (₹21,316); lowest: About to Sleep (₹1,295).
- **What factors are associated with higher customer value?** Historical profit = orders x AOV x margin; the number of orders accounts for 62% of the variance in log profit, AOV 39%, margin -1% (margins differ little between customers). For FUTURE value, the most important model feature is Frequency (permutation importance). These are associations, not causes.
- **Which customers have high historical value?** 397 customers (historical profit >= P80); 300 of them are also frequent and recent; 52 have not bought for >= 180 days.
- **Which customers may represent future value opportunities?** 119 customers are in the top 20% of estimated 12-month value without being in the top 20% of historical value (flag Future_Value_Opportunity). The estimate is approximate: out-of-time R² 0.27, and the top 20% predicted captured 41% of actual next-year profit in the test.
- **How can CLV support retention and marketing decisions?** Historical profit CLV identifies whom the business depends on today; the estimated 12-month value and the at-risk flag show where value may be lost or gained next. Both can size and prioritise retention effort (final recommendations are a later step).

All estimated values should be read as: *the model estimates an expected next-12-month profit of approximately ₹X under the defined assumptions and prediction period* - not as what a customer will generate.

## 13. Limitations

1. **Synthetic data.** Patterns come from the Step 2 generator, not from a real business.
2. **Modest predictive accuracy.** Out-of-time R² 0.27; per-customer errors are large relative to typical values. Use for ranking and prioritising, not for exact per-customer rupee figures.
3. **Non-stationarity.** Active customers grew from 1,137 (2023) to 1,716 (2025); the model under-estimated the 2025 total (90%). A different future year could move either way.
4. **One out-of-time test.** Only one hold-out year exists (2025); results could differ in another year.
5. **Left-censored tenure** for customers existing before 2023; historical value is a minimum for them.
6. **No churn label.** 'Potentially at-risk' is a documented inactivity rule, not observed churn.
7. **Group-level estimate** for customers with no order in the last 12 months (one average value).
8. **12-month horizon only is validated.** The 3-year figure is illustrative, undiscounted and untested.
9. **Associations, not causes.** Feature importance does not show that changing a behaviour changes value.
10. **Gamma-Gamma rejected; BG/NBD not selected** - see section 4.

## 14. Next analytical steps

- Step 8 (revenue prediction & business driver analysis) can reuse the time-based panel design and the leakage checks built here.
- Re-validate the CLV model when a new year of data arrives (roll the cutoffs forward by 12 months).
- If real cost-of-capital and retention-cost data become available, add discounting and margin-after-marketing to the multi-year value.

## 15. Validation

| Check | Value | Pass |
|---|---|---|
| One row per customer (no duplicate IDs) | 0 | True |
| Customers = valid population (>= 1 Delivered order) = Step 5 RFM | 1,984 vs 1,984 vs 1,984 | True |
| Revenue reconciles with cleaned Delivered sales | ₹6.01 Cr vs ₹6.01 Cr | True |
| Profit reconciles with cleaned Delivered profit | ₹1.40 Cr vs ₹1.40 Cr | True |
| Revenue - cost = profit for every customer | all customers | True |
| Orders and revenue match Step 5 Frequency / Monetary | per customer | True |
| Tenure non-negative; first <= last <= reference date | min tenure 7 d | True |
| No leakage: every feature date < cutoff (train & test) | train max 2023-12-31, test max 2024-12-31 | True |
| Time integrity: target dates >= cutoff; training target window ends before test target window | train target from 2024-01-01, test target from 2025-01-01 | True |
| No leakage: no target, RFM/cluster label or ID among model features | Recency_Days, Frequency, AOV, ... | True |
| Target window exists in the data (no invented future) | test target ends 2025-12-31 | True |
| Feature selection reproduces MODEL_FEATURES; final VIF <= 5 | max VIF 3.52 | True |
| Reproducible: refit with fixed random_state gives identical predictions | random_state=42 | True |
| Reported metrics recomputed from saved test predictions | R² 0.2705 | True |
| Every customer has one estimate and a method label; estimates >= 0 | 1,984 estimates | True |
| CLV by RFM and by cluster reconcile with the customer total | ₹1.40 Cr | True |
| Every assumption documented | 16 assumptions in clv_assumptions.csv | True |
| Saved model + preprocessor (reloaded from models/) reproduce the estimates | clv_model.pkl, clv_preprocessor.pkl | True |

## 16. Assumptions

| Assumption | Detail |
|---|---|
| Revenue rule | Only Delivered lines count as revenue, cost and profit (Step 3 rule); Returned/Cancelled = 0. |
| Customer population | 1,984 customers with >= 1 Delivered order; the 16 customers with no Delivered order have no value to measure (same population as Step 5). |
| Reference date | 2026-01-01 (latest order date + 1 day, Step 5). |
| Historical CLV | Observed 2023-2025 totals. Not a forecast; tenure is left-censored for customers who existed before 2023, so their historical value is a minimum. |
| Future-value target | Future_Profit_12M: Delivered profit in the 12 months after a cutoff. |
| Feature window | 12 months before the cutoff (same length at every cutoff so the training and test features are comparable). |
| Tenure feature | Capped at 365 days because the training cutoff only has 12 months of history. |
| Model population | Customers with >= 1 Delivered order in the 12 months before the cutoff. |
| Model features | 8 features after removing exact identities and VIF > 5: Recency_Days, Frequency, AOV, Profit_Margin, Avg_Discount, Categories, Tenure_Days_Capped, Return_Rate. |
| Customers outside the model population | Given the observed average next-12-month profit of the equivalent group at the 2025 cutoff (₹830, n = 307); a group-level estimate, not customer-specific. |
| Stationarity | The estimate assumes next year behaves like the training years. Activity grew in 2025, and the out-of-time test shows the model under-estimates totals (see bias ratio). |
| Illustrative 3-year value | 12-month estimate x (1 + r + r^2) with r = pooled observed annual repeat rate 0.839; no discounting (no cost of capital is available for the company); NOT validated. |
| Inactivity | >= 180 days without a purchase = 'potentially at-risk', never 'churned' (many such customers bought again - see sensitivity table). |
| Probabilistic models | BG/NBD fitted and tested as a benchmark; Gamma-Gamma rejected because spend and frequency are correlated. |
| Predictions floored at zero | Negative model outputs are set to ₹0 (a customer's expected purchases cannot be negative). |
| Synthetic data | SYNTHETIC DATA - generated for academic demonstration only |

## 17. Output files

- `data/processed/customer_value_history.csv` - observed historical value per customer
- `data/processed/customer_clv.csv` - historical + estimated value, RFM segment, cluster, value flags
- `data/processed/clv_modeling_dataset.csv` - train / test / scoring panels (features + targets)
- `models/clv_model.pkl`, `models/clv_preprocessor.pkl`, `models/clv_model_metadata.json`
- `outputs/tables/clv_*.csv` - 26 tables
- `outputs/figures/` - clv_distribution.png, clv_value_concentration.png, clv_revenue_vs_profit.png, customer_tenure_vs_value.png, frequency_vs_clv.png, recency_vs_clv.png, clv_by_rfm_segment.png, clv_by_ml_cluster.png, clv_inactivity_threshold.png, clv_model_comparison.png, clv_actual_vs_predicted.png, clv_feature_importance.png, clv_high_value_groups.png
