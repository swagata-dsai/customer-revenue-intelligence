# Trick Questions — Live Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

Twenty-two questions that invite a confident wrong answer. The mark is in the
nuance, not the speed. Complements `09_trick_questions.md` from Step 16.

**1. What is the difference between RFM segmentation and K-Means
segmentation?**
RFM is **rule-based**, not machine learning: I define the scores and the
thresholds, so every assignment is explainable and checkable by hand. K-Means
is **unsupervised learning**: it finds groups by minimising within-cluster
variance, with no knowledge of my rules. That independence is why their
agreement — ARI 0.3952 — counts as evidence.

**2. Can K-Means predict future customers?**
No. K-Means is descriptive, not predictive. It can **assign** a new customer to
the nearest existing centroid once that customer has recency, frequency and
monetary values — but it forecasts nothing, and it cannot place a customer with
no purchase history at all.

**3. Is correlation the same as causation?**
No, and the discount finding is exactly why I am careful. The
0% band shows 29.31% margin against
20.43%, but deeper discounts may be applied to already
low-margin situations. The recommendation is therefore an experiment, not a
price change.

**4. Does a high-revenue customer always have high CLV?**
No. Revenue is not profit — RFM's M is revenue, so a customer buying often in a
low-margin category can contribute less profit than a smaller buyer in a
high-margin one. And historical value is not forward value: a large customer
who has gone quiet has high history and low expected future, which is exactly
the 52-customer list.

**5. Does a high R² automatically mean the model is good?**
No. R² says nothing about bias, ranking ability, or whether the errors have a
heavy tail. My customer-value model has R² 0.2705 but Spearman
0.4869 — poor at levels, good at ranking. A high R² can also be a
leakage symptom rather than a success.

**6. Can you use accuracy for regression?**
No. Accuracy is a classification metric — the share of correct labels — and a
continuous prediction is essentially never exactly correct. Regression uses
MAE, RMSE, R², and for this project WAPE, because MAPE breaks near zero.

**7. Why shouldn't you randomly split time-series data?**
Because it trains on the future to predict the past. Random splitting destroys
the ordering the task depends on and produces a score that cannot be achieved
in practice. Everything time-dependent here uses a chronological split, and the
forecast uses rolling-origin backtesting.

**8. Can Power BI replace machine learning?**
No. Power BI aggregates and presents; it does not fit a K-Means model, a
regression or a time-series model. It consumes the results my Python pipeline
produced.

**9. Can Streamlit itself train a model?**
Streamlit is just Python, so a script could technically call `fit()` — but
mine deliberately does not. The app loads the persisted `.pkl` artefacts and
never refits, because a model retrained on every page load would be
non-reproducible and slow.

**10. Does PCA improve model accuracy automatically?**
No. PCA discards variance to reduce dimensionality — it can help with
collinearity or noise, and it can equally throw away signal. With three
features there was nothing to gain, which is why I used it for visualisation
only.

**11. Your project has 18,670 rows. Is that big data?**
No, and I would not call it that. It fits in memory on a laptop. The interest
here is the integration and the discipline, not the volume — and I have an
answer for what would change at ten million rows.

**12. A silhouette of 0.3534 — is your clustering wrong?**
Not wrong; weakly separated. The algorithm converged, the clusters are stable
at ARI 0.95, and their profiles differ materially. What the number
says is that the customer base is a continuum, which is true of most customer
bases.

**13. Is your forecast a guarantee of future revenue?**
No. It is a projection of one series from its own history, with an 80% interval
of ₹1.00 Cr to ₹2.16 Cr and an expected error of
14.56%. It knows nothing about prices, promotions or competitors.

**14. Champions are your best customers — should you spend most of the budget
on them?**
Not automatically. They are already buying, so the marginal return on
contacting a Champion may be lower than on reactivating an At Risk customer
holding 11.26% of revenue. This project measures value, not marginal
response, and I will not claim the latter.

**15. You removed 149 duplicates — what if they were real repeat
orders?**
They were exact duplicate rows including order ID; a genuine repeat purchase
would carry a different order ID and date. The removal is logged, and the
generator's injection log confirms they were injected duplicates.

**16. If the model predicts ₹0 for a customer, should the business drop them?**
No. 53.0% of customer-quarters are genuinely zero, so zero is the
model's most common output and carries very little information about any
individual. At R² 0.0557 it should not drive an individual decision at
all.

**17. Is a 23.35% margin good?**
Unknowable from this data — there is no benchmark, no competitor and no target
in a synthetic catalogue. What I can say is internal: margin **rose** from
22.65% to 23.90% while revenue grew.

**18. October is your best month — is that seasonality?**
It is a regularity in all three years, but the formal seasonality test on
36 observations does not confirm a stable pattern. Calling it
seasonality would overstate what 36 months can support.

**19. The top 20% produce 64.33% — isn't that just Pareto, so nothing
new?**
The principle predicts concentration; it does not tell you who, or how much in
this base — and here it is 64.33%, not the proverbial 80%. The
contribution is the named list and the fact that two independent methods
identify the same group.

**20. Can synthetic data represent real customer behaviour?**
Structurally, to a degree — skew, seasonality, discounting, returns and missing
fields are all present. Behaviourally, no: there is no motivation, no
competitive response, no macroeconomic effect. It demonstrates method; it does
not support conclusions about a market.

**21. If your pipeline is automated, what did you actually do?**
Chose the definitions, the rules and the validation. Deciding that revenue
means delivered lines only, that K must pass three pre-declared tests, that a
forecast must beat both naive baselines, and that no number may be typed into a
report by hand — then building the audit that checks all of it.

**22. Could more tuning have given you a better R²?**
A little, probably not much. The ceiling here is set by zero inflation, not by
hyperparameters. The real improvement is structural — a two-stage model — and
that is in future scope, not claimed as done.
