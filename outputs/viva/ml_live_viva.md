# Machine Learning Viva — Live Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

Twenty answers, each matching the actual implementation.

**1. Why K-Means?**
Because it scales, produces centroids that read directly as business profiles,
and is reproducible from a fixed seed. Hierarchical clustering gives a
dendrogram but is O(n²) and still needs a cut point chosen by judgement; DBSCAN
labels outliers as noise, which does not suit a base where every customer must
land somewhere. Neither was implemented — I considered them and chose K-Means
for those reasons.

**2. What is clustering?**
Grouping observations so that members of a group are more similar to each other
than to members of other groups, without any labels to learn from. It is
unsupervised: there is no correct answer to check against.

**3. Why standardize the RFM features?**
Because K-Means uses Euclidean distance and the three features are on wildly
different scales — monetary value runs to lakhs, frequency is a count under 50.
Without scaling, monetary value alone would determine every cluster. All three
are also heavily right-skewed, so the persisted pipeline applies
log1p -> StandardScaler (sklearn Pipeline saved in rfm_scaler.pkl).

**4. What is the elbow method?**
Plotting inertia — the sum of squared distances to assigned centroids — against
K and looking for where the improvement flattens. It is a heuristic, not a
rule: inertia always falls as K rises, and the elbow is often ambiguous, which
is why I did not rely on it alone.

**5. What is the silhouette score?**
For each point, how much closer it is to its own cluster than to the nearest
other cluster, on a scale of −1 to +1. The mean across all points is
0.3534 here. That is modest, and I report it as modest — customer
data rarely forms well-separated spheres.

**6. How did you choose K?**
By three rules fixed **before** I saw any results: at least 3
clusters, no cluster smaller than 5% of the base, and bootstrap
stability of Adjusted Rand Index at least 0.90. Only among the values
that passed all three did silhouette decide. K = 4, silhouette
0.3534, stability 0.95. The evaluation table shows every
K tested with its eligibility, including the ones that failed.

**7. What is PCA?**
Principal component analysis — a linear projection into fewer dimensions that
keeps as much variance as possible, with the components ordered by how much
each explains.

**8. Why use PCA?**
Only to visualise the clusters in two dimensions. PC1 explains 71.50% and
PC2 23.59% — 95.09% together — so the picture is faithful rather
than lossy. PCA was **not** a model input: clustering runs on all three scaled
features. At three dimensions, reducing first would have added an unexplained
transformation for no benefit.

**9. What is CLV?**
The value a customer represents over their relationship with the business. This
project reports it as two distinct quantities rather than one number.

**10. Historical value vs predicted CLV?**
Historical value is **measured**: ₹1.40 Cr of delivered profit already
earned, mean ₹7,068 against median ₹3,893 per customer.
Forward value is **estimated** by a random forest trained out of
time, MAE ₹2,793, R² 0.2705, Spearman 0.4869. They
are never added together and the estimate is never presented as a guarantee.

**11. Why did you select your revenue prediction model?**
By the rule fixed in advance: simplest model within 2% of the best validation RMSE (fixed in advance). Random forest, gradient
boosting and a tuned forest were all fitted; none beat the linear model by
enough to pass that tolerance, so the simpler and interpretable model was kept.
That is a signal-strength result, not a claim that linear models are better.

**12. Why a chronological train/test split?**
Because the task is predicting the future from the past. A random split would
let the model learn from quarters that come after the ones it is tested on,
which inflates the score and means nothing operationally. My split is
4,788 train (features 2023-01-01..2024-09-30 -> targets 2024-01-01..2024-12-31), 2,692 validation
(targets 2025-01-01..2025-06-30), 2,913 test (targets 2025-07-01..2025-12-31).

**13. What is data leakage?**
Using information at training time that would not be available at prediction
time — either directly, or through a feature computed over the target window.
It matters because it produces a model that scores well in development and
fails in production.

**14. How did you prevent leakage?**
Every feature in the panel is computed strictly from data before its cutoff. To
verify rather than assume, a leakage audit samples rows and recomputes their
features **directly from the transaction table with independent logic**, then
compares. If the pipeline had leaked, the two would disagree. They did not.

**15. What is MAE?**
Mean absolute error — the average absolute difference between prediction and
actual, in the target's own units. ₹5,658 on the prediction test
split.

**16. What is RMSE?**
Root mean squared error. Errors are squared before averaging, so large misses
are penalised more heavily. ₹11,232 here — far above the MAE, which
tells you the error distribution has a heavy tail.

**17. What is R²?**
The share of variance in the target explained by the model, relative to simply
predicting the mean. 0.0557 on prediction — small. The naive
previous-quarter baseline scores -0.5700, so the model is better than
the baseline while still explaining little.

**18. What is feature importance?**
How much each feature contributes to the model's predictions. I used
**permutation importance** — shuffle a feature, measure how much the error
rises — because it is model-agnostic and not biased toward high-cardinality
features the way built-in tree importance is. Value drivers:
Frequency, Avg_Discount, Recency_Days, AOV. Prediction drivers: Orders_12M, Main_Category, Share_Books, AOV_12M.

**19. What is overfitting?**
A model that fits the noise in the training data, so its score does not survive
unseen data. My evidence against it is the direction of the metrics on an
out-of-time test split, and the fact that a linear model with
24 features on 4,788 rows has very little
capacity to overfit.

**20. How did you validate the models?**
Differently by task, because the tasks differ. Clustering: internal indices,
bootstrap stability and external agreement with the RFM scheme. Customer value:
5-fold cross-validation within the training cutoff to select, then an
out-of-time test. Prediction: chronological split plus an independent leakage
audit. Forecasting: rolling-origin backtesting over 7 folds, with
a hard requirement to beat both naive baselines. And the whole project carries
135 automated checks, 134 passing.
