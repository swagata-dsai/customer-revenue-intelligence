# Difficult Professor Questions — Live Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

Thirty questions aimed at the weak points, answered honestly. This file
complements `08_challenging_questions.md` from Step 16 — that one is written
for reading, this one for answering aloud under pressure.

**1. Why should we trust your segmentation?**
Because it was validated three ways rather than asserted. Internally:
silhouette 0.3534. For stability: bootstrap mean ARI
0.95. Externally: an independent rule-based scheme finds
substantially the same high-value group, ARI 0.3952. And K was chosen by
rules fixed before the results.

**2. How do you know the clusters are meaningful?**
Because their business profiles differ materially — cluster 0 is
18.35% of customers and 55.67% of revenue — and because a method
that knows nothing about my rules found the same high-value group. Statistical
separation is modest; business separation is not.

**3. What if K-Means gives unstable clusters?**
That is exactly what the stability rule tests. I resampled with replacement,
re-clustered and compared partitions by ARI; K = 4 scores
0.95 against a pre-declared floor of 0.90. Values that
failed it were rejected regardless of their silhouette.

**4. What if the dataset changes?**
The segments would shift, because the quintile cut-offs are relative to the
base. The pipeline is fully re-runnable, so re-scoring is one command — but
nothing in the current system would **tell** you the distribution had moved.
That is a genuine gap, named in future scope as drift monitoring.

**5. What happens with missing values in new data?**
The cleaning rules run on any extract, and each rule has a defined treatment.
What the system does not have is a monitored threshold — if a new extract
arrived 40% empty, the rules would treat it and report it, but nothing would
halt the pipeline. In production that gate should exist.

**6. What happens with unseen categories?**
The prediction preprocessor one-hot encodes the categorical features. An unseen
category at scoring time would be handled by the encoder's configuration rather
than crashing, but it would carry no learned signal — effectively a neutral
row. For a genuinely new product category, the right answer is to refit, not to
score.

**7. What if the model performs poorly?**
One of mine does, and I report it rather than hide it: prediction R²
0.0557. The response is to state the boundary of legitimate use —
portfolio level, bias 1.12%, not individual customers — and to name
the structural cause, 53.0% zero customer-quarters.

**8. Why isn't correlation enough?**
Because correlation measures linear co-movement and says nothing about
direction or mechanism. The discount finding is the clearest case: the
0% band shows 29.31% margin against
20.43%, but discounts may be **applied to** low-margin
situations rather than causing them. Only an experiment separates those.

**9. Why can't revenue prediction simply use historical revenue?**
It can, and that is my baseline — the naive previous-quarter rule. It scores
MAE ₹6,423 and R² -0.5700. The model beats it
(₹5,658, 0.0557), which is the only reason it earns its place.
If it had not beaten the baseline I would have said so.

**10. How did you avoid leakage?**
By construction and then by test. Every feature is computed strictly before its
cutoff; then a leakage audit samples rows and recomputes those features
directly from the transaction table with independent logic. If the pipeline had
leaked, the two would disagree.

**11. Why should management trust the forecast?**
Trust the interval, not the point. The honest expected error is the backtest
mean of 14.56% over 7 folds, not the favourable
single-split 7.77%. And the model had to beat both naive
baselines to be selected at all.

**12. What would change with real company data?**
Business-supplied segment thresholds instead of my quintiles; a churn label the
business defines; cost-to-serve so value becomes contribution rather than gross
profit; and a real test of whether the segment structure transfers.

**13. How would you deploy this system?**
Schedule the pipeline stages; version model artefacts with their metadata;
serve predictions through a small API rather than in-process loading;
containerise the app behind authentication; add drift and performance
monitoring. None of it exists today — the app runs locally.

**14. How would you handle 10 million transactions?**
The pandas in-memory approach stops being appropriate. I would push the
aggregations into SQL — most of the EDA and the RFM base table are already
expressible as queries — use chunked or columnar reads for the modelling
panel, and fit K-Means with MiniBatchKMeans. The analysis would not change;
the execution layer would.

**15. How would you monitor model drift?**
Three signals: input distributions against the training distribution, the
prediction distribution over time, and realised accuracy when actuals arrive —
which for a quarterly target means one honest score per quarter. Not
implemented.

**16. Your silhouette is 0.3534. Most textbooks call that weak.**
That is a fair reading and I do not dispute it. The base is a continuum, not
four separated populations. Usability comes from the profile differences and
the independent agreement, not from separation.

**17. Could a different K tell a completely different story?**
Different boundaries, yes. What is stable is the high-value group — it appears
at every eligible K and under the rule-based scheme too. The middle of the base
is where assignment is sensitive, which is precisely where I say the rules are
arbitrary.

**18. You generated the data yourself. Didn't you find what you put in?**
Partly, and that is the honest limit. The generator sets skewed value,
seasonality, discounting and returns. It does not set the ARI between two
schemes, the silhouette, or how predictable next-quarter revenue turns out to
be — and that last one came out the opposite of what I expected.

**19. Why is your customer-value R² only 0.2705?**
Because twelve-month-ahead individual profit is genuinely hard to predict from
eight behavioural features. The more useful number is Spearman
0.4869 and top-20% capture 41.46% — it ranks well, which
is how it is used.

**20. Did your audit ever actually fail?**
Yes, which is the test of whether it is real. It caught documentation
describing recency as a churn warning in a project with no churn event; a stale
figure quoting an older audit count; a filename in the appendix that did not
match the persisted model; and four pipeline commands in the user manual naming
functions that do not exist. All were fixed at source.

**21. What is the weakest link in the project?**
The customer-level prediction model. Everything upstream is either measured or
validated; that is the one component whose individual output I would not act
on.

**22. If a colleague inherited this tomorrow, what would break first?**
Nothing would break, but it would go stale silently. There is no scheduling and
no monitoring, so the models would keep returning confident numbers from an
increasingly old training window.

**23. Why did a linear regression beat two ensembles?**
It did not beat them outright — it tied within the tolerance I had fixed in
advance (simplest model within 2% of the best validation RMSE (fixed in advance)). Given a tie, the simpler interpretable model wins
by rule. That is a signal-strength finding, not a claim about model families.

**24. Why should I believe your selection rules were fixed in advance?**
Because they are published with the results and the evaluation tables include
the options that **failed** them. If I had chosen after the fact, the failing
candidates would not be in the table.

**25. What does your project prove?**
That value in this base is concentrated and identifiable by two independent
methods, and that company-level revenue is forecastable while individual
revenue is not. It proves nothing causal, and it proves nothing about a real
business.

**26. If I gave you one more month, what would you do?**
The two-stage prediction model, because it addresses the one structural
weakness. Then drift monitoring, because without it the whole thing decays
invisibly.

**27. Why no churn model, when churn is the standard use case?**
Because the dataset defines no churn event — no contract, no cancellation, no
explicit lapse. Any label would have been invented by me and then predicted by
me, which proves nothing. I report recency-based inactivity instead and never
use the word churn for a result.

**28. Your report says "complete". Can you prove that?**
No — and I would distinguish the claims. Consistent and reconciled I can
evidence with 135 checks. Complete is a judgement: it means I
believe nothing material is missing, and that is not provable.

**29. What would make you distrust your own results?**
If the SQL layer disagreed with the Python pipeline, since they are independent
implementations of the same definitions. Or if the leakage audit found a
mismatch. Those are the two checks designed to catch me being wrong.

**30. Why does this project deserve a good grade?**
Not because the models are strong — one is not. Because every number is
traceable to the file that produced it, every model was chosen by a rule fixed
before the results, weak results are reported as weak, an association is never
called causation, and the integration is tested by 135 automated
checks rather than asserted.
