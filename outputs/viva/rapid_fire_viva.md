# Rapid-Fire Viva — 55 Questions

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

One or two sentences each. Answer fast, and where a number exists, say it.

## Python and Pandas

1. **What is Python used for here?** Every stage — cleaning, analysis,
   modelling, forecasting and the application.
2. **What is a DataFrame?** A labelled two-dimensional table; the project's
   cleaned dataset is 18,670 rows × 51 columns.
3. **`loc` vs `iloc`?** `loc` selects by label, `iloc` by integer position.
4. **What does `groupby` do?** Splits rows into groups, applies an aggregation,
   and combines the results — the basis of every KPI here.
5. **What does `merge` do?** Joins two DataFrames on a key, like a SQL JOIN.
6. **What is `apply` and why avoid it?** It runs a function row-wise; it is slow
   compared with vectorised operations, so it is used sparingly.
7. **Why NumPy?** The numerical layer under pandas; used directly for the
   `log1p` and `arcsinh` transforms.
8. **What does `log1p` do?** Computes log(1+x) — compresses right-skew and
   handles zeros safely.
9. **What is joblib for?** Persisting and reloading the trained models as
   `.pkl` artefacts.
10. **How many Python modules are in the project?** 41, about
    30,690 lines.

## SQL

11. **How many tables?** 11 tables and 2 views.
12. **How many queries?** 57 — 37 analysis and
    20 business.
13. **WHERE vs HAVING?** WHERE filters before aggregation, HAVING after.
14. **INNER vs LEFT JOIN?** INNER keeps only matches; LEFT keeps all left rows
    with NULLs where there is none.
15. **What is a CTE?** A named temporary result defined with `WITH`; used in 27
    queries.
16. **What is a window function?** Computes across related rows without
    collapsing them; used in 35 queries.
17. **ROW_NUMBER vs RANK?** ROW_NUMBER is unique even for ties; RANK gives ties
    the same value then skips.
18. **What does `SUM() OVER ()` give?** The grand total on every row — how
    percentage-of-total columns are built.
19. **What are LAG and LEAD?** Read the previous or next row in a window; the
    basis of year-over-year growth.
20. **Why a normalised database?** To remove repetition, enforce keys, and make
    SQL a genuinely independent implementation.

## Statistics and EDA

21. **Mean vs median here?** Mean profit per customer ₹7,068 against
    median ₹3,893 — the gap is right-skew.
22. **What is skewness?** Asymmetry in a distribution; R, F and M are all
    right-skewed, which is why they are log-transformed.
23. **What are quantiles?** Cut points dividing a distribution into equal
    groups; RFM uses quintiles.
24. **How did you detect outliers?** The 1.5×IQR rule — flagged and inspected,
    never removed.
25. **What is correlation?** Linear co-movement from −1 to +1; computed across
    the numeric measures during EDA.
26. **What is EDA?** Understanding structure, quality and relationships before
    modelling.
27. **What is feature engineering?** Creating variables with business meaning;
    28 columns added here.

## RFM and clustering

28. **What is RFM?** Recency, frequency and monetary scoring into named
    segments — 11 here.
29. **Your reference date?** 2026-01-01 — the latest order date plus one
    day.
30. **How many customers scored?** 1,984; 16
    excluded for having no delivered purchase.
31. **Champions?** 334 customers, 16.84% of the base,
    53.83% of revenue.
32. **What is K-Means?** Partitions data into K clusters by minimising
    within-cluster variance.
33. **What is a centroid?** The mean position of a cluster's members.
34. **What is inertia?** Sum of squared distances to assigned centroids — what
    K-Means minimises.
35. **Your K and silhouette?** K = 4, silhouette 0.3534.
36. **How was K chosen?** Three rules fixed in advance, then highest silhouette
    among the eligible values.
37. **What is ARI?** Chance-corrected agreement between two partitions —
    0.3952 between RFM and clusters.
38. **What is PCA used for here?** Visualisation only — 95.09% of
    variance in two components.

## Customer value, prediction, forecasting

39. **What is CLV?** Customer lifetime value; here reported as measured
    historical and estimated forward, separately.
40. **Historical value total?** ₹1.40 Cr of delivered profit.
41. **Which value model?** Random forest — R² 0.2705, Spearman
    0.4869.
42. **How many at-risk high-value customers?** 52, holding
    ₹26.51 L.
43. **Prediction target?** Each customer's delivered revenue in the next
    quarter.
44. **Prediction model and score?** Linear regression, test R² 0.0557,
    MAE ₹5,658.
45. **Why is it weak?** 53.0% of customer-quarters have a zero
    actual value.
46. **What is data leakage?** Using information unavailable at prediction time;
    audited here and none found.
47. **What is MAE?** Average absolute error in the target's units.
48. **What is RMSE?** Root mean squared error — penalises large misses more.
49. **What is R²?** Share of variance explained relative to the mean.
50. **When does MAPE break?** Near zero actuals — which is why WAPE
    (127.83%) is used for prediction.
51. **Forecast model and horizon?** Theta: Theta (seasonality auto-tested), 6 months,
    2026-01 to 2026-06.
52. **Forecast error?** Backtest mean MAPE 14.56% over
    7 folds — quote this, not the test split.

## Delivery and business

53. **Power BI measures?** 84 DAX measures,
    48/48 validated against SQL.
54. **Streamlit pages and tests?** 12 pages,
    40/40 headless tests pass.
55. **The headline business finding?** The top 20% of customers produce
    64.33% of revenue, and two independent methods identify the same
    group.
