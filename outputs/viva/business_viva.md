# Business Viva — Live Answers

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

**1. What business problem does your project solve?**
It closes the gap between recording transactions and taking decisions.
Aggregate reporting cannot distinguish a month carried by a few large customers
from one built on a broad base, so it cannot guide retention effort. This
platform answers the customer-level questions: who is valuable, who is going
quiet, what will they spend, and what will total revenue be.

**2. Who would use this system?**
Three audiences with three surfaces. A sales or account manager uses the
Customer Segmentation page to work the at-risk list. A category or regional
manager uses Power BI to slice revenue and margin for their own area. A
planner uses the Sales Forecast for capacity and cash. The report and the audit
serve whoever has to trust the numbers.

**3. How can management use customer segmentation?**
By setting a different action per segment rather than treating all customers
alike. Champions (16.84% of customers, 53.83% of revenue)
get protection and early access. At Risk (11.26% of revenue) gets
reactivation. Lost gets low-cost contact at most. The K-Means clusters are the
cross-check: where the two schemes disagree, the customer is near a boundary
and deserves a human look.

**4. How can the company identify high-value customers?**
Three converging routes, which is what makes the answer trustworthy: the RFM
Champions segment, K-Means cluster 0 (18.35% of customers,
55.67% of revenue), and the revenue concentration curve. All three
point at the same group, and the top decile alone carries 45.39% of
revenue.

**5. How can the company reduce the risk of losing customers?**
By acting on **inactivity**, which is what this data supports — not churn,
which it does not define. The median gap between orders is 54
days, so a customer silent for several multiples of that is behaving
differently. The concrete output is the 52 high-value customers
inactive for 180+ days, holding ₹26.51 L between them.

**6. How can CLV support marketing decisions?**
By ranking customers on estimated forward twelve-month profit rather than on
past spend. The model's Spearman of 0.4869 says it ranks well even
though its R² of 0.2705 says it predicts levels poorly — so it orders a
queue of attention. Its top-20% capture is 41.46%.

**7. How can revenue prediction support planning?**
At portfolio level only. Total bias is 1.12%, so aggregated
predictions are close to unbiased and can inform a quarterly expectation.
Individual predictions explain almost nothing (0.0557) and must not set
a target for one customer. Being clear about that boundary is part of the
answer.

**8. How can forecasting support inventory and cash decisions?**
The 6-month forecast is ₹1.58 Cr with an 80% interval of
₹1.00 Cr to ₹2.16 Cr, against ₹1.50 Cr delivered in the
previous six months. The right use is to commit against the lower bound and
size capacity against the point estimate — plan against the interval, not the
number.

**9. How can the dashboard support management?**
By removing the analyst from the loop for routine questions. A manager slices
revenue by date, region, category or segment over 84 conformed
measures, so "revenue" means one thing everywhere. The Streamlit application
adds what a dashboard cannot do: run the actual models and return downloads.

**10. What business decisions can be made from your project?**
Where to put retention effort (the top decile and the 52-customer
list); how to manage category mix (Electronics at
10.85% margin versus Beauty at
46.49%); whether to run a discount experiment; what to plan
next quarter against; and where **not** to spend — there is no regional margin
problem, and the Lost segment carries little revenue.

**11. What are the limitations?**
Synthetic data; a 36-month history; weak individual prediction;
a univariate forecast; association not causation; no churn label; Power BI
Desktop unavailable so its pages are design mockups; no user testing; and no
deployment or monitoring.

**12. What would you improve with real company data?**
Four things specifically. I would replace my quintile cut-offs with
business-supplied thresholds, so a segment means something absolute. I would
ask the business to define a churn event and build a supervised model against
it. I would add cost-to-serve so customer value becomes contribution rather
than gross profit. And I would validate whether the segment structure that
emerges matches the one found here — which is the real test of whether the
method transfers.

**13. What is the return on this project?**
The project measured no acquisition cost or campaign response, so I cannot
compute one, and I will not invent a figure. What I can say is where value sits
— 64.33% of revenue in the top 20% of customers, and
₹26.51 L of it already earned but going quiet.

**14. If you had to defend one recommendation, which?**
Give the top revenue decile a named owner and review it monthly. It costs
almost nothing, it protects 45.39% of revenue, and it does not depend on
any model being accurate.

**15. Which recommendation would you be most careful about?**
The discount one. The evidence is strong — the zero-discount band is
best-margin in 6 of 6 categories — but it is
observational. Deeper discounts may be applied to situations that are already
low-margin. That is why the recommendation is an experiment, not a price change.
