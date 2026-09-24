# Revenue Prediction Modelling & Business Driver Analysis - Step 8

> **SYNTHETIC DATA - generated for academic demonstration only.** Results illustrate the method on the Step 2 synthetic dataset (seed 42).

Reproduce: `python src/prediction.py` (about 1 minute). Notebook: `notebooks/06_revenue_prediction.ipynb`.

## 1. Objective

Build a reproducible, leakage-free model that predicts each existing customer's revenue in the next quarter, measure how accurately that is possible on unseen quarters, and describe which measurable characteristics the model associates with revenue.

**Prediction vs causal impact.** A prediction model learns *associations* in historical data: "customers with more past orders tended to spend more next quarter". It does **not** show that changing a feature (e.g. cutting discounts) would *cause* revenue to change; that needs an experiment or a causal design. Every importance, coefficient and scenario below is an association under the model.

## 2. Prediction unit and target

| Item | Definition |
|---|---|
| Prediction unit | Customer x quarter: every customer with >= 1 Delivered order in the 12 months before a quarter start |
| Target variable | `Next_Quarter_Revenue` = Delivered Sales (Rs) in the 3 months starting at the cutoff; 0 if no purchase |
| Feature period | the 12 months before the cutoff (3-month sub-window for recent activity) |
| Prediction period | the calendar quarter starting at the cutoff |
| Business purpose | plan next-quarter revenue from the existing customer base; see what the model associates with it |
| Why not transactions? | predicting a line's Sales from Quantity x Price is an identity, not a planning problem |
| Why not category/region-month? | time-series forecasting of aggregates is Step 9; the customer unit supports customer, product and regional features and segment analysis |

**Coverage.** The panel covers revenue from customers already active; new or reactivated customers are not in it:

| Cutoff | Customers | Quarter_Total_Revenue | Revenue_Covered | Coverage_% |
|---|---|---|---|---|
| 2024-01-01 | 1137 | ₹45.05 L | ₹36.89 L | 81.9% |
| 2024-04-01 | 1181 | ₹39.36 L | ₹32.95 L | 83.7% |
| 2024-07-01 | 1213 | ₹43.67 L | ₹37.50 L | 85.9% |
| 2024-10-01 | 1257 | ₹69.62 L | ₹60.73 L | 87.2% |
| 2025-01-01 | 1328 | ₹56.99 L | ₹49.06 L | 86.1% |
| 2025-04-01 | 1364 | ₹64.83 L | ₹58.83 L | 90.8% |
| 2025-07-01 | 1380 | ₹69.66 L | ₹60.90 L | 87.4% |
| 2025-10-01 | 1533 | ₹80.79 L | ₹68.02 L | 84.2% |

54.0% of all customer-quarters have zero revenue. Customer-level MAPE is therefore undefined and is not used; WAPE (total absolute error / total actual) and quarter-total error are reported instead.

## 3. Train / validation / test periods (chronological)

| Split | Cutoffs | Feature_Data_From | Feature_Data_To | Target_Period | Rows | Customers | Zero_Target_% | Mean_Target |
|---|---|---|---|---|---|---|---|---|
| train | 2024-01-01, 2024-04-01, 2024-07-01, 2024-10-01 | 2023-01-01 | 2024-09-30 | 2024-01-01 to 2024-12-31 | 4788 | 1487 | 57.6% | ₹3,510 |
| validation | 2025-01-01, 2025-04-01 | 2024-01-01 | 2025-03-31 | 2025-01-01 to 2025-06-30 | 2692 | 1441 | 48.7% | ₹4,008 |
| test | 2025-07-01, 2025-10-01 | 2024-07-01 | 2025-09-30 | 2025-07-01 to 2025-12-31 | 2913 | 1560 | 53.0% | ₹4,426 |

No shuffling. Training targets end 2024-12-31, validation targets 2025-01-01 to 2025-06-30, test targets 2025-07-01 to 2025-12-31. Model choice and tuning used validation only; the final model was refit on train + validation and scored on test (see the design-iteration note in section 4).

## 4. Feature engineering

Candidate features (28 numeric + 5 categorical), all computed from data dated before the cutoff:

- **Customer history:** recency, revenue (3m / 12m / same quarter last year), profit and margin, orders (3m / 12m), quantity, AOV, average discount, return rate, tenure (capped at 365 days), a point-in-time RFM score, main payment method, acquisition status.
- **Product:** category revenue shares, main category, number of categories, average unit price, product-demand index (how popular the customer's products were across all customers), main-category revenue trend.
- **Regional:** region, the region's share of company revenue and of active customers, regional revenue trend.
- **Time:** the calendar quarter being predicted, company revenue trend.

**Selection (training rows only):**

| Feature | Group | Decision | Reason | VIF_All_Candidates | VIF_Final_Set | Spearman_with_Target_(train) |
|---|---|---|---|---|---|---|
| Recency_Days | Customer history | Kept | core measure (always kept) | 4.6 | 3.0 | -0.20 |
| Rev_3M | Customer history | Kept | VIF <= 10 | 10.6 | 9.3 | +0.20 |
| Rev_12M | Customer history | Excluded | exact identity = AOV_12M x Orders_12M | 2,509.5 |  | +0.21 |
| Rev_Same_Quarter_Last_Year | Customer history | Kept | VIF <= 10 | 1.9 | 1.8 | +0.08 |
| Profit_12M | Customer history | Excluded | exact identity = AOV_12M x Orders_12M x Profit_Margin_12M | 1.6 |  | +0.24 |
| Profit_Margin_12M | Customer history | Kept | core measure (always kept) | 11.0 | 8.8 | -0.04 |
| Orders_3M | Customer history | Kept | VIF <= 10 | 10.5 | 10.0 | +0.19 |
| Orders_12M | Customer history | Kept | core measure (always kept) | 586.1 | 4.8 | +0.23 |
| Quantity_12M | Customer history | Excluded | VIF 53.9 > 10 | 54.6 |  | +0.23 |
| AOV_12M | Customer history | Kept | core measure (always kept) | 1,207.1 | 6.2 | +0.13 |
| Avg_Discount_12M | Customer history | Kept | core measure (always kept) | 3.6 | 2.6 | -0.09 |
| Return_Rate_12M | Customer history | Kept | VIF <= 10 | 1.0 | 1.0 | +0.10 |
| Tenure_Days_Capped | Customer history | Kept | VIF <= 10 | 2.5 | 2.5 | +0.08 |
| RFM_Score_at_Cutoff | Customer history | Excluded | VIF 18.7 > 10 | 27.8 |  | +0.25 |
| Categories_12M | Product | Kept | VIF <= 10 | 4.5 | 4.3 | +0.22 |
| Avg_Unit_Price_12M | Product | Kept | core measure (always kept) | 54.0 | 13.5 | +0.11 |
| Product_Demand_Index | Product | Kept | VIF <= 10 | 2.1 | 1.9 | +0.01 |
| Main_Category_Trend | Product | Kept | VIF <= 10 | 3.0 | 3.0 | +0.04 |
| Share_Fashion | Product | Excluded | perfectly collinear with other features | inf |  | +0.03 |
| Share_Home_Kitchen | Product | Kept | VIF <= 10 | inf | 5.5 | +0.10 |
| Share_Electronics | Product | Excluded | VIF 10.8 > 10 | inf |  | +0.08 |
| Share_Beauty | Product | Kept | VIF <= 10 | inf | 7.2 | +0.06 |
| Share_Books | Product | Kept | VIF <= 10 | inf | 7.5 | +0.03 |
| Share_Sports | Product | Kept | VIF <= 10 | inf | 5.7 | +0.08 |
| Region_Revenue_Share_3M | Regional | Excluded | VIF 15.8 > 10 | 17.6 |  | -0.02 |
| Region_Customer_Share_12M | Regional | Excluded | VIF 281.1 > 10 | 281.2 |  | -0.02 |
| Region_Rev_Trend | Regional | Kept | VIF <= 10 | 8.2 | 1.9 | +0.03 |
| Company_Rev_Trend | Time / company | Excluded | perfectly collinear with other features | inf |  | +0.04 |

Final model: 19 numeric + 5 categorical features. Protected core measures above the VIF limit: Avg_Unit_Price_12M (13.5). RFM_Score_at_Cutoff was excluded as redundant (it is built from recency, orders and revenue).

**Design iteration (documented for transparency).** The first specification used company and regional revenue *levels* (Rs). They grow every year and take only 4 distinct values in training, so a linear model used them as a time trend. That first specification was run end-to-end once (including the test split; test R² 0.05-0.07 for the ML models). The changes that followed were decided from validation and coefficient diagnostics:

| Specification | Distinct_Training_Values_of_Company_Level | Val_R2 | Val_RMSE | Val_Total_Bias_% |
|---|---|---|---|---|
| Final feature set (shares / ratios) | 4 | 0.038 | ₹9,436 | -20.7% |
| + Company_Rev_3M and Region_Rev_3M (Rs levels) | 4 | -0.112 | ₹10,142 | -95.4% |

**Encoding / preprocessing** (one scikit-learn `ColumnTransformer`, fitted on training rows only): numeric -> median imputation -> arcsinh for skewed money/count features -> standardisation; categorical -> most-frequent imputation -> one-hot encoding (`handle_unknown='ignore'`). One-hot was chosen because none of the categorical variables is ordinal and it keeps coefficients readable; target encoding was not needed.

## 5. Leakage prevention

| Variable | Why it is available | Decision / reason |
|---|---|---|
| Next_Quarter_Revenue / Next_Quarter_Orders | Target-period values | Future information - target only |
| Future Sales / Profit / Quantity / Discount / activity | Any line dated >= cutoff | Would reveal the answer; all feature windows end the day before the cutoff |
| RFM_Segment, R/F/M scores (Step 5) | Computed on 2023-2025 incl. target quarters | Look-ahead; replaced by RFM_Score_at_Cutoff; used only to group errors |
| Cluster_ID (Step 6) | K-Means fitted on 2023-2025 incl. target quarters | Look-ahead; used only to group errors |
| Historical_Profit_CLV / Estimated CLV (Step 7) | Full-period totals and a model fitted on 2024-2025 targets | Look-ahead |
| Sales = Quantity x Unit_Price x (1 - Discount) of the same order | Same-period identity | Trivial, not a planning problem |
| Customer_Name, Customer_ID | Identifiers | No predictive meaning; privacy |
| Gender, Customer_Age, City, State | Demographics / high-cardinality location | Not needed for planning; Region carries location; avoids demographic profiling |

**Automated checks**

| Check | Pass |
|---|---|
| Max feature date < cutoff at every cutoff | True |
| Min target date >= cutoff at every cutoff | True |
| Target window <= 3 months after cutoff | True |
| No target / future / full-period label column among model features | True |
| Correlation check: no feature has /Spearman/ > 0.95 with the target (training rows) | True |

The full per-feature timing register is `outputs/tables/revenue_feature_catalog.csv`.

## 6. Baselines and models (validation)

Baselines (no fitting): previous quarter's revenue; same quarter last year; the 12-month quarterly mean. Models: Linear regression (interpretable), Random forest, Gradient boosting - all in scikit-learn pipelines.

| Model | Type | Train_R2 | Val_MAE | Val_RMSE | Val_R2 | Val_WAPE_% | Val_Total_Bias_% | Overfit_Gap_R2 |
|---|---|---|---|---|---|---|---|---|
| Baseline: previous quarter (naive) | Baseline | -0.810 | ₹5,904 | ₹12,816 | -0.775 | 147.3% | +17.3% | -0.034 |
| Baseline: same quarter last year (seasonal naive) | Baseline | -0.541 | ₹5,588 | ₹12,884 | -0.794 | 139.4% | -21.8% | 0.253 |
| Baseline: 12-month quarterly mean | Baseline | -0.075 | ₹4,915 | ₹10,161 | -0.116 | 122.6% | -5.6% | 0.041 |
| Linear regression | ML model | 0.059 | ₹4,523 | ₹9,436 | 0.038 | 112.9% | -20.7% | 0.022 |
| Random forest | ML model | 0.437 | ₹5,003 | ₹9,466 | 0.031 | 124.8% | +11.2% | 0.406 |
| Gradient boosting | ML model | 0.472 | ₹5,037 | ₹9,753 | -0.028 | 125.7% | +6.9% | 0.500 |

- **MAE**: average absolute rupee error per customer-quarter. **RMSE**: like MAE but penalises large misses more. **R²**: share of variance explained (0 = no better than predicting the average; negative = worse). **WAPE**: total absolute error / total actual revenue. **Total bias**: (sum predicted - sum actual) / sum actual.
- The tree models fit training data much better than validation (large overfit gap); the linear model has almost no gap.

## 7. Hyperparameter tuning

Candidate: **Random forest** (the tree model with the lower default validation RMSE). Randomized search, 15 settings sampled with `random_state=42`; each fitted on train and scored on validation (chronological hold-out, no future rows in training).

Parameters tested: `n_estimators` in [100, 200, 300]; `max_depth` in [None, 6, 10, 16]; `min_samples_split` in [2, 10, 20]; `min_samples_leaf` in [1, 3, 5, 10, 20]; `max_features` in [0.3, 0.5, 0.8, 1.0].

| Iteration | n_estimators | max_depth | min_samples_split | min_samples_leaf | max_features | Val_RMSE | Val_MAE | Val_R2 | Train_R2 |
|---|---|---|---|---|---|---|---|---|---|
| 13 | 100 | None | 10 | 20 | 0.3 | ₹9,340 | ₹4,745 | 0.057 | 0.190 |
| 4 | 100 | 6 | 2 | 5 | 0.3 | ₹9,357 | ₹4,782 | 0.054 | 0.218 |
| 10 | 100 | 10 | 10 | 10 | 0.3 | ₹9,364 | ₹4,808 | 0.052 | 0.256 |
| 12 | 200 | 10 | 20 | 20 | 0.5 | ₹9,365 | ₹4,785 | 0.052 | 0.196 |
| 15 | 200 | 10 | 20 | 5 | 0.5 | ₹9,426 | ₹4,909 | 0.040 | 0.314 |
| 9 | 200 | 6 | 10 | 5 | 0.8 | ₹9,439 | ₹4,833 | 0.037 | 0.258 |
| 2 | 300 | 6 | 2 | 5 | 0.8 | ₹9,441 | ₹4,825 | 0.037 | 0.256 |
| 1 | 200 | 6 | 20 | 5 | 1.0 | ₹9,445 | ₹4,851 | 0.036 | 0.229 |

Best parameters: `{'n_estimators': 100, 'min_samples_split': 10, 'min_samples_leaf': 20, 'max_features': 0.3, 'max_depth': None}`. Validation RMSE ₹9,340 vs ₹9,466 for the default (-1.3%); tuning mainly reduced overfitting (train R² 0.19).

## 8. Model selection

Rule (set before modelling): keep models within 2% of the best validation RMSE; choose the simplest model family (linear < random forest < boosting); within a family the lower validation RMSE wins. Criteria considered: validation error, overfitting gap, interpretability, business usability and compute cost.

| Model | Val_RMSE | Val_MAE | Val_R2 | Train_R2 | Overfit_Gap_R2 | Within_2%_of_Best | Selected |
|---|---|---|---|---|---|---|---|
| Linear regression | ₹9,436 | ₹4,523 | 0.038 | 0.059 | 0.022 | True | True |
| Random forest | ₹9,466 | ₹5,003 | 0.031 | 0.437 | 0.406 | True | False |
| Gradient boosting | ₹9,753 | ₹5,037 | -0.028 | 0.472 | 0.500 | False | False |
| Random forest (tuned) | ₹9,340 | ₹4,745 | 0.057 | 0.190 | 0.132 | True | False |

**Final model: Linear regression.** It is within 2% of the best validation RMSE, has the lowest validation MAE, almost no overfitting gap, readable coefficients and negligible compute cost.

## 9. Model evaluation (test, 2025-Q3 and Q4)

| Model | Type | MAE | RMSE | R2 | WAPE_% | Spearman | Total_Bias_% | Selected |
|---|---|---|---|---|---|---|---|---|
| Baseline: previous quarter (naive) | Baseline | ₹6,423 | ₹14,483 | -0.570 | 145.1% | 0.129 | +4.3% | False |
| Baseline: same quarter last year (seasonal naive) | Baseline | ₹5,880 | ₹13,557 | -0.376 | 132.9% | 0.158 | -12.1% | False |
| Baseline: 12-month quarterly mean | Baseline | ₹5,436 | ₹11,466 | 0.016 | 122.8% | 0.224 | -3.8% | False |
| Linear regression | ML model | ₹5,658 | ₹11,232 | 0.056 | 127.8% | 0.175 | +1.1% | True |
| Random forest | ML model | ₹5,762 | ₹11,265 | 0.050 | 130.2% | 0.171 | +8.0% | False |
| Gradient boosting | ML model | ₹5,845 | ₹11,383 | 0.030 | 132.1% | 0.158 | +10.1% | False |
| Random forest (tuned) | ML model | ₹5,554 | ₹11,148 | 0.070 | 125.5% | 0.201 | +2.3% | False |

- Final model: MAE **₹5,658**, RMSE **₹11,232**, R² **0.056**, WAPE 127.8%, total bias +1.1%.
- Versus the best baseline (12-month quarterly mean): RMSE ₹11,466 -> ₹11,232 and R² 0.016 -> 0.056, but MAE is higher (₹5,436 baseline). The naive previous-quarter rule is much worse (R² -0.57).
- Highest test R² of any method: 0.070 (Random forest (tuned)); not used for selection.
- **Customer-level next-quarter revenue is only weakly predictable here**: most customers buy 0-1 times a quarter, so the amount any single customer spends is dominated by timing noise.
- **Quarter totals** (sum of predictions): 2025-Q3 -18.9% (naive +6.4%), 2025-Q4 +19.1% (naive +2.4%). The seasonal (quarter) effect is learned from a single year of training quarters and did not transfer well; for quarter totals the naive rule was closer on the test quarters.

**Quarterly totals (all splits)**

| Target_Period | Split | Actual_Revenue | Predicted_Revenue | Error_% | Naive_Baseline | Naive_Error_% |
|---|---|---|---|---|---|---|
| 2024-Q1 | train (in-sample fit) | ₹36.89 L | ₹36.89 L | -0.0% | ₹48.43 L | +31.3% |
| 2024-Q2 | train (in-sample fit) | ₹32.95 L | ₹32.95 L | -0.0% | ₹45.05 L | +36.7% |
| 2024-Q3 | train (in-sample fit) | ₹37.50 L | ₹37.50 L | -0.0% | ₹39.36 L | +5.0% |
| 2024-Q4 | train (in-sample fit) | ₹60.73 L | ₹60.73 L | -0.0% | ₹43.67 L | -28.1% |
| 2025-Q1 | validation (out-of-sample) | ₹49.06 L | ₹46.38 L | -5.5% | ₹69.62 L | +41.9% |
| 2025-Q2 | validation (out-of-sample) | ₹58.83 L | ₹39.17 L | -33.4% | ₹56.99 L | -3.1% |
| 2025-Q3 | test (out-of-sample) | ₹60.90 L | ₹49.38 L | -18.9% | ₹64.83 L | +6.4% |
| 2025-Q4 | test (out-of-sample) | ₹68.02 L | ₹80.99 L | +19.1% | ₹69.66 L | +2.4% |

## 10. Feature importance

Permutation importance of the final pipeline on the test split (each raw feature, including a whole categorical variable, is shuffled; the rise in MAE is recorded). Read it as *the model relied more heavily on this feature*, not *this feature causes revenue*.

| Rank | Feature | Group | Permutation_MAE_Increase | Permutation_Std |
|---|---|---|---|---|
| 1 | Orders_12M | Customer history | ₹236 | ₹17 |
| 2 | Main_Category | Product | ₹41 | ₹7 |
| 3 | Share_Books | Product | ₹41 | ₹9 |
| 4 | AOV_12M | Customer history | ₹19 | ₹3 |
| 5 | Categories_12M | Product | ₹13 | ₹4 |
| 6 | Acquisition_Status | Customer history | ₹9 | ₹3 |
| 7 | Profit_Margin_12M | Customer history | ₹6 | ₹3 |
| 8 | Share_Home_Kitchen | Product | ₹5 | ₹2 |
| 9 | Share_Sports | Product | ₹5 | ₹2 |
| 10 | Avg_Discount_12M | Customer history | ₹4 | ₹2 |
| 11 | Main_Payment_Method | Customer history | ₹4 | ₹3 |
| 12 | Recency_Days | Customer history | ₹4 | ₹1 |
| 13 | Share_Beauty | Product | ₹3 | ₹1 |
| 14 | Tenure_Days_Capped | Customer history | ₹2 | ₹3 |
| 15 | Return_Rate_12M | Customer history | ₹1 | ₹3 |

**Largest linear-regression coefficients** (Rs per +1 SD of the transformed feature, or vs. the reference category):

| Encoded_Feature | Coefficient | Transform |
|---|---|---|
| Main_Category_Books | +2,533 | one-hot |
| Orders_12M | +1,616 | arcsinh + standardise |
| Target_Quarter_Q4 | +1,178 | one-hot |
| Main_Category_Home & Kitchen | -1,077 | one-hot |
| Main_Category_Fashion | -854 | one-hot |
| Main_Payment_Method_Unknown | -790 | one-hot |
| Target_Quarter_Q3 | -620 | one-hot |
| Share_Books | -580 | standardise |
| Tenure_Days_Capped | -460 | standardise |
| Categories_12M | +408 | standardise |
| Region_North | +397 | one-hot |
| Target_Quarter_Q1 | -349 | one-hot |

Small categories (e.g. Books, 73 test rows) get large, unstable coefficients; Main_Category and the category shares remain partly collinear (one-hot VIF up to ~16).

## 11. Error analysis (test)

**By target quarter**

| Target_Period | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| 2025-Q3 | 1380 | ₹60.90 L | ₹49.38 L | ₹5,137 | 116.4% | -18.9% |
| 2025-Q4 | 1533 | ₹68.02 L | ₹80.99 L | ₹6,126 | 138.1% | +19.1% |

**By region**

| Region | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| Central | 371 | ₹15.48 L | ₹15.52 L | ₹5,316 | 127.4% | +0.3% |
| East | 383 | ₹18.08 L | ₹15.82 L | ₹5,784 | 122.6% | -12.5% |
| North | 652 | ₹28.97 L | ₹32.60 L | ₹6,040 | 135.9% | +12.5% |
| South | 784 | ₹35.34 L | ₹34.63 L | ₹5,629 | 124.9% | -2.0% |
| West | 723 | ₹31.06 L | ₹31.80 L | ₹5,452 | 126.9% | +2.4% |

**By main category**

| Main_Category | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| Beauty | 261 | ₹6.93 L | ₹8.44 L | ₹4,083 | 153.7% | +21.7% |
| Books | 73 | ₹1.29 L | ₹2.12 L | ₹3,524 | 198.9% | +63.7% |
| Electronics | 935 | ₹56.40 L | ₹54.97 L | ₹7,098 | 117.7% | -2.5% |
| Fashion | 947 | ₹36.94 L | ₹35.09 L | ₹5,205 | 133.4% | -5.0% |
| Home & Kitchen | 587 | ₹24.14 L | ₹25.41 L | ₹5,284 | 128.5% | +5.3% |
| Sports | 110 | ₹3.21 L | ₹4.35 L | ₹4,461 | 152.8% | +35.5% |

**By actual revenue range**

| Revenue_Range | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| Rs 0 (no purchase) | 1543 | ₹0 | ₹64.98 L | ₹4,242 |  |  |
| Rs 1-5k | 767 | ₹16.89 L | ₹30.76 L | ₹2,582 | 117.2% | +82.1% |
| Rs 5k-15k | 378 | ₹32.64 L | ₹20.21 L | ₹3,857 | 44.7% | -38.1% |
| Rs 15k-40k | 167 | ₹41.45 L | ₹10.38 L | ₹18,604 | 75.0% | -75.0% |
| Rs 40k+ | 58 | ₹37.94 L | ₹4.04 L | ₹58,457 | 89.4% | -89.4% |

**By ML cluster (Step 6)**

| Cluster | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| C0: High-Value, Active | 719 | ₹93.82 L | ₹46.65 L | ₹10,499 | 80.5% | -50.3% |
| C1: Low-Value, Active | 461 | ₹7.12 L | ₹12.22 L | ₹2,483 | 160.8% | +71.6% |
| C2: Mid-Value, Lapsing | 1418 | ₹27.53 L | ₹63.12 L | ₹4,873 | 251.0% | +129.3% |
| C3: Low-Value, Inactive | 315 | ₹46,130 | ₹8.38 L | ₹2,785 | 1902.1% | +1716.3% |

**By RFM segment (Step 5)**

| RFM_Segment | Rows | Actual_Revenue | Predicted_Revenue | MAE | WAPE_% | Bias_% |
|---|---|---|---|---|---|---|
| Champions | 664 | ₹91.41 L | ₹44.02 L | ₹10,986 | 79.8% | -51.8% |
| Loyal Customers | 449 | ₹19.10 L | ₹20.98 L | ₹5,436 | 127.8% | +9.8% |
| Potential Loyalists | 226 | ₹6.61 L | ₹6.14 L | ₹2,948 | 100.7% | -7.2% |
| Recent Customers | 47 | ₹69,639 | ₹1.15 L | ₹1,753 | 118.3% | +64.7% |
| Promising | 69 | ₹1.36 L | ₹1.50 L | ₹1,552 | 78.5% | +9.9% |
| Needs Attention | 221 | ₹3.79 L | ₹7.94 L | ₹3,775 | 220.0% | +109.3% |
| About to Sleep | 170 | ₹1.11 L | ₹4.98 L | ₹3,171 | 484.1% | +346.8% |
| Can't Lose Them | 157 | ₹1.27 L | ₹9.24 L | ₹6,197 | 767.8% | +629.3% |
| At Risk | 489 | ₹2.68 L | ₹22.86 L | ₹4,770 | 871.1% | +753.7% |
| Hibernating | 275 | ₹88,678 | ₹8.33 L | ₹3,155 | 978.5% | +839.1% |
| Lost | 146 | ₹0 | ₹3.24 L | ₹2,349 |  |  |

**Patterns**

- Predictions are pulled toward the average: customers who spent Rs 40k+ in the quarter were under-predicted by 89%, while customers with no purchase received an average prediction of ₹4,211.
- Regions are similar (MAE ₹5,316 to ₹6,040); bias ranges -12% to +13%.
- Small categories are over-predicted (Books +64%, Sports +35%).
- By segment, the pattern mirrors regression to the mean: the highest-value segments are under-predicted and lapsing segments over-predicted. Segment labels are full-period (look-ahead) and used only for this grouping.

## 12. Business driver analysis

| Driver | Group | Importance_Rank | Model_Evidence | Data_Evidence | Limitation |
|---|---|---|---|---|---|
| Orders_12M | Customer history | 1 | Permutation: shuffling it raises test MAE by ₹236 | Spearman +0.26 with next-quarter revenue; mean revenue by feature quartile ₹2,003 (lowest) -> ₹7,079 (highest) | Association with past behaviour; does not show that changing it would change revenue |
| Main_Category | Product | 2 | Permutation: shuffling it raises test MAE by ₹41 | Mean next-quarter revenue: highest Electronics ₹4,904, lowest Books ₹2,180 | Product mix is correlated with price level and customer type; not a causal effect |
| Share_Books | Product | 3 | Permutation: shuffling it raises test MAE by ₹41 | Spearman +0.04 with next-quarter revenue; mean revenue by feature quartile ₹3,018 (lowest) -> ₹4,542 (highest) | Product mix is correlated with price level and customer type; not a causal effect |
| AOV_12M | Customer history | 4 | Permutation: shuffling it raises test MAE by ₹19 | Spearman +0.15 with next-quarter revenue; mean revenue by feature quartile ₹2,020 (lowest) -> ₹5,086 (highest) | Association with past behaviour; does not show that changing it would change revenue |
| Categories_12M | Product | 5 | Permutation: shuffling it raises test MAE by ₹13 | Spearman +0.23 with next-quarter revenue; mean revenue by feature quartile ₹1,942 (lowest) -> ₹6,584 (highest) | Product mix is correlated with price level and customer type; not a causal effect |
| Acquisition_Status | Customer history | 6 | Permutation: shuffling it raises test MAE by ₹9 | Mean next-quarter revenue: highest Existing before 2023 ₹4,092, lowest Acquired 2023-2025 ₹3,304 | Association with past behaviour; does not show that changing it would change revenue |
| Profit_Margin_12M | Customer history | 7 | Permutation: shuffling it raises test MAE by ₹6 | Spearman -0.08 with next-quarter revenue; mean revenue by feature quartile ₹4,344 (lowest) -> ₹2,585 (highest) | Association with past behaviour; does not show that changing it would change revenue |
| Share_Home_Kitchen | Product | 8 | Permutation: shuffling it raises test MAE by ₹5 | Spearman +0.11 with next-quarter revenue; mean revenue by feature quartile ₹2,337 (lowest) -> ₹3,900 (highest) | Product mix is correlated with price level and customer type; not a causal effect |
| Share_Sports | Product | 9 | Permutation: shuffling it raises test MAE by ₹5 | Spearman +0.10 with next-quarter revenue; mean revenue by feature quartile ₹2,829 (lowest) -> ₹4,993 (highest) | Product mix is correlated with price level and customer type; not a causal effect |
| Avg_Discount_12M | Customer history | 10 | Permutation: shuffling it raises test MAE by ₹4 | Spearman -0.08 with next-quarter revenue; mean revenue by feature quartile ₹3,879 (lowest) -> ₹2,212 (highest) | Association with past behaviour; does not show that changing it would change revenue |
| Main_Payment_Method | Customer history | 11 | Permutation: shuffling it raises test MAE by ₹4 | Mean next-quarter revenue: highest COD ₹4,018, lowest Unknown ₹835 | Association with past behaviour; does not show that changing it would change revenue |
| Recency_Days | Customer history | 12 | Permutation: shuffling it raises test MAE by ₹4 | Spearman -0.20 with next-quarter revenue; mean revenue by feature quartile ₹5,129 (lowest) -> ₹2,058 (highest) | Association with past behaviour; does not show that changing it would change revenue |

**Categorical drivers - what the data shows (train + validation rows)**

| Feature | Level | Rows | Mean_Next_Quarter_Revenue | Share_With_Purchase_% |
|---|---|---|---|---|
| Region | Central | 948 | ₹3,426 | 45.8% |
| Region | East | 950 | ₹3,508 | 46.8% |
| Region | North | 1679 | ₹4,133 | 46.4% |
| Region | South | 2020 | ₹3,678 | 44.5% |
| Region | West | 1883 | ₹3,530 | 45.5% |
| Main_Category | Beauty | 759 | ₹2,650 | 39.9% |
| Main_Category | Books | 257 | ₹2,180 | 39.3% |
| Main_Category | Electronics | 2297 | ₹4,904 | 49.8% |
| Main_Category | Fashion | 2283 | ₹3,120 | 43.4% |
| Main_Category | Home & Kitchen | 1517 | ₹3,608 | 46.1% |
| Main_Category | Sports | 367 | ₹3,165 | 47.1% |
| Main_Payment_Method | COD | 1074 | ₹4,018 | 48.1% |
| Main_Payment_Method | Card | 1464 | ₹3,504 | 45.4% |
| Main_Payment_Method | Net Banking | 711 | ₹3,553 | 45.6% |
| Main_Payment_Method | UPI | 3504 | ₹3,735 | 44.8% |
| Main_Payment_Method | Unknown | 41 | ₹835 | 39.0% |
| Main_Payment_Method | Wallet | 686 | ₹3,652 | 46.8% |
| Acquisition_Status | Acquired 2023-2025 | 3826 | ₹3,304 | 42.8% |
| Acquisition_Status | Existing before 2023 | 3654 | ₹4,092 | 48.6% |
| Target_Quarter | Q1 | 2465 | ₹3,487 | 43.4% |
| Target_Quarter | Q2 | 2545 | ₹3,607 | 46.1% |
| Target_Quarter | Q3 | 1213 | ₹3,092 | 39.2% |
| Target_Quarter | Q4 | 1257 | ₹4,831 | 55.2% |

**What cannot be concluded:** none of these drivers is shown to cause revenue. Frequency, AOV and product mix move together with customer type and price level; discounts are not randomly assigned; seasonality rests on one training year.

## 13. Scenario analysis (model-based)

| Scenario | Change_Applied | Total_Predicted_Revenue | Change_vs_Current_% | Rows_Outside_Training_Range_% |
|---|---|---|---|---|
| Current (actual test features) | none | ₹1.30 Cr | +0.0% | 0.0% |
| Purchase frequency +10% | orders (12m, 3m) and recent revenue history x 1.10 (AOV unchanged) | ₹1.38 Cr | +5.5% | 0.3% |
| Average order value +10% | AOV, unit price and recent revenue history x 1.10 (orders unchanged) | ₹1.31 Cr | +0.6% | 0.0% |
| Average discount -2 percentage points | Avg_Discount_12M - 0.02 (floored at 0); nothing else | ₹1.32 Cr | +1.3% | 0.0% |

Under the model's assumptions, raising purchase frequency by 10% produces an estimated change in predicted test-period revenue of +5.5%, a 10% higher AOV +0.6%, and 2 percentage points less discount +1.3%. These are **model-based scenarios, not guaranteed outcomes**: the discount result reflects that lower-discount customers historically spent more, not that removing discounts would raise revenue (it could reduce purchases). Linked features were changed together; almost all scenario rows stay inside the training range.

## 14. Business interpretation

- **Can future revenue be predicted from historical/business features?** Partly. On the unseen test quarters (2025-Q3, Q4) the final model explains R² 0.06 of the variation in customer-level next-quarter revenue, vs -0.57 for the naive previous-quarter rule. Single-quarter totals for the active base missed by -18.9% (2025-Q3) and +19.1% (2025-Q4), less accurate than the naive rule for totals.
- **Which variables are most useful for predicting revenue?** By permutation importance on the test set: Orders_12M, Main_Category, Share_Books, AOV_12M, Categories_12M.
- **How accurately can revenue be predicted?** MAE ₹5,658 per customer-quarter, RMSE ₹11,232, WAPE 127.8%, total bias +1.1% over the two test quarters combined. 53.0% of test customer-quarters had zero revenue, so individual predictions are very uncertain; errors largely cancel over many customers and two quarters, but not reliably within a single quarter.
- **Which customer, product, pricing, discount and regional characteristics are associated with revenue?** Customer purchase history dominates (see driver table). Product, price and region features rank lower: Main_Category rank 2; Avg_Discount_12M rank 10; Region rank 16; Avg_Unit_Price_12M rank 20; Target_Quarter rank 24. These are associations, not causes.
- **How can predicted revenue support business planning?** It gives an expected next-quarter revenue per existing customer that can rank customers and be summed by region or category (test bias by region -12% to +13%, by main category -5% to +64%). It should not be the only basis for a single-quarter revenue target (seasonality is poorly estimated), and new customers must be planned separately.

## 15. Limitations

1. **Synthetic data** from the Step 2 generator.
2. **Low customer-level accuracy** (test R² 0.06); the 12-month-mean baseline has a lower MAE. Use predictions for aggregate planning and ranking, not for individual promises.
3. **Seasonality learned from one year** (4 training quarters); quarter totals missed by up to 19% on test.
4. **Non-stationary growth**: activity rose each year; scale-free features reduce but do not remove this.
5. **Coverage**: only customers active in the prior 12 months (82-91% of quarterly revenue).
6. **One test period** (two quarters); results could differ in other periods.
7. **Residual collinearity** between main category and category shares; small categories have unstable effects.
8. **Association, not causation**: importance, coefficients and scenarios describe the model, not interventions.
9. **Design iteration**: the first specification was run once on the test split before the level features were removed (section 4); later choices were made on validation evidence.

## 16. Validation

| Area | Check | Value | Pass |
|---|---|---|---|
| Target | Target = Delivered Sales in the 3 months after each cutoff (recomputed independently) | 10,393 rows | True |
| Target | Target dates only inside [cutoff, cutoff + 3 months) | 2024-01-01 .. 2025-12-31 | True |
| Leakage | No feature uses data on/after its cutoff | max feature date < cutoff at all 8 cutoffs | True |
| Leakage | Preprocessor fitted on training rows only (validation step); final refit on train+validation only | final fit rows 7,480 = train 4,788 + validation 2,692 | True |
| Time | Training targets end before validation targets start; validation before test | 2024-12-31 < 2025-01-01; 2025-06-30 < 2025-07-01 | True |
| Time | Test split unused during selection/tuning | selection table uses Val_* columns only | True |
| Model | Feature selection (training rows) reproduces the model feature list; non-protected VIF <= 10 | 19 numeric features, max VIF 10.0 (protected above 10: Avg_Unit_Price_12M 13.5) | True |
| Model | Baselines exist | 3 baselines | True |
| Model | Multiple ML models evaluated | 4 models | True |
| Model | Reported test metrics recomputed from the saved prediction table | R² 0.0557 | True |
| Predictions | Predicted values finite | 2913 | True |
| Predictions | Prediction table reconciles with the test split (rows, customers, actual total) | 2,913 rows, ₹1.29 Cr | True |
| Predictions | Errors correctly calculated (error = predicted - actual; % only where actual > 0) | 1,543 rows with actual = 0 have no % | True |
| Predictions | No duplicate (customer, cutoff) keys in the panel | 0 | True |
| Predictions | Error-analysis merges keep row counts (many_to_one) | 2,913 | True |
| Reproducibility | Refit with fixed random_state gives identical test predictions | random_state=42 | True |
| Reproducibility | Saved pipeline (reloaded from models/) reproduces the test predictions; metadata saved | revenue_prediction_model.pkl, revenue_model_metadata.json | True |

## 17. Output files

- `data/processed/revenue_modeling_dataset.csv` - customer x quarter panel (all candidate features + target)
- `models/revenue_prediction_model.pkl` (full pipeline), `models/revenue_prediction_preprocessor.pkl`, `models/revenue_model_metadata.json`
- `outputs/tables/revenue_*.csv` - 27 tables (incl. `revenue_predictions.csv`, `revenue_feature_importance.csv`, `revenue_prediction_by_rfm.csv`, `revenue_prediction_by_cluster.csv`)
- `outputs/figures/` - revenue_model_comparison.png, actual_vs_predicted_revenue.png, prediction_error_distribution.png, revenue_prediction_timeline.png, revenue_feature_importance.png, prediction_error_by_region.png, prediction_error_by_category.png, prediction_error_by_revenue_range.png, predicted_revenue_by_cluster.png, predicted_revenue_by_rfm.png
