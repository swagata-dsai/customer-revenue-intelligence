# Professor Presentation Questions — Exact Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

**"Explain your project."**
"It's a customer revenue intelligence platform. It takes retail transaction
data — synthetic, generated for academic demonstration — and carries it through
cleaning, exploratory analysis, two independent customer segmentations, value
analysis, next-quarter revenue prediction and company-level forecasting. Every
metric is then reproduced independently in SQL and delivered through a Power BI
semantic model and a working 12-page application. The headline
finding is that value is concentrated: the top 20% of customers produce
64.33% of ₹6.01 Cr in revenue, and two independent methods identify
the same group."

**"What is innovative about your project?"**
"Not the techniques — RFM, K-Means, regression and Theta are all established,
and I claim no novelty in any of them. What is unusual is the integration and
the traceability: one validated dataset and one revenue definition flowing
through every stage, reconciled against an independent SQL implementation, with
every number in the report and the deck read from the pipeline's own output
files rather than typed in. The 135-check audit is part of that
— it tests the integration instead of asserting it."

**"What did YOU personally implement?"**
"All of it — the data generator, the cleaning rules, every analysis module, the
four models, the SQL layer, the Power BI semantic model and DAX library, the
Streamlit application and its test suite, and the audit. What I did not do is
invent any of the methods; those come from the literature, which is cited."

**"What was the most difficult part?"**
"Accepting the prediction result. I expected moderate accuracy and got R²
0.0557. The tempting move was to keep trying models until one looked
better, but I had fixed the selection rule in advance — simplest model within 2% of the best validation RMSE (fixed in advance) —
so the honest path was to report it as weak and explain the structural cause:
53.0% of customer-quarters have no order at all. Technically, the
hardest part was building the leakage audit that recomputes features
independently to verify the panel."

**"What did you learn?"**
"Three things. That defining the rules before seeing the results changes what
you conclude — it is the difference between analysis and rationalisation. That
reconciliation across implementations is worth more than any single model,
because it is what makes the numbers trustworthy. And that reporting a weak
result honestly is more defensible than hiding it — the contrast between a
forecastable company series and unpredictable individual customers is itself
the finding."

**"What is the business value?"**
"A short, specific action list rather than a report. The top revenue decile
carries 45.39% of revenue and now has a named list. The
52 high-value customers who have gone quiet, holding
₹26.51 L, are a working contact list. And category strategy becomes a
mix question — Electronics at 10.85% margin versus
Beauty at 46.49% — rather than a single revenue
target. Whether acting on these pays is an empirical question the business
would have to test; I have not measured campaign response."

**"What is the biggest limitation?"**
"The data is synthetic, so the methods transfer but the numbers describe no
real business. After that, the customer-level prediction model — it is usable
at portfolio level and not for an individual customer, and I say so wherever it
appears."

**"If I give you real company data, what will you change?"**
"Four things. Replace my quintile cut-offs with business-supplied thresholds,
so a segment means something absolute rather than a position in this base. Ask
the business to define a churn event, so a churn model becomes possible. Add
cost-to-serve, so customer value becomes contribution rather than gross profit.
And test whether the segment structure that emerges matches this one — that is
the real check on whether the method transfers."

**"If your model gives a wrong prediction, what will you do?"**
"For the customer-level model, nothing surprising — it is wrong often, which is
why its stated use is portfolio-level and why every page shows its accuracy
beside its output. For the forecast, a miss outside the 95% interval would mean
either misspecification or something outside the revenue series moved, and
since the model is univariate it cannot see prices or promotions. The response
is to refit with external regressors, which is in future scope. What I would
not do is adjust the model until it fits one bad quarter."

**"If the customer segments change next month, why?"**
"Most likely because the cut-offs are relative. The quintile boundaries are
computed on the current base, so a shift in the base moves the boundaries even
if individual behaviour is unchanged. Recency also moves mechanically — the
reference date advances, so every customer's recency grows unless they buy.
Genuine behavioural change is the third possibility, and distinguishing it from
the first two is exactly what drift monitoring would do. That is not
implemented."

**"How can this project be deployed in a real company?"**
"In stages. First, schedule the pipeline so the outputs refresh on a cadence.
Second, version the model artefacts with their metadata and serve predictions
through a small API rather than loading them in-process. Third, containerise
the application behind authentication. Fourth, add drift and performance
monitoring so degradation is visible. The semantic model is the piece that is
already production-shaped — it reads from SQL views, so pointing it at a
warehouse is a connection change, not a rewrite. None of this is done today,
and the application runs locally."
