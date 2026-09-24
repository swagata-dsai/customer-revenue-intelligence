# Live Demonstration Script

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

Six versions of the same explanation. Read them aloud once each — they are
written to be spoken, not read silently.

---

## 30 seconds

"My project is a customer revenue intelligence platform. It takes retail
transaction data and carries it through cleaning, customer segmentation, value
analysis, revenue prediction and forecasting, and delivers the results through
a Power BI model and a working 12-page application. The dataset
is synthetic, generated for academic demonstration. The headline finding is
that value is concentrated — the top 20% of customers produce 64.33% of
₹6.01 Cr in revenue."

---

## 1 minute

"First, the business problem. Retail businesses record transactions far faster
than they turn them into decisions — revenue gets reported by month and
category, but the questions that matter are customer-level: who is valuable,
who is going quiet, what will they spend next.

My project builds one platform that answers those. The dataset is synthetic,
generated with a fixed seed — 18,819 raw order lines cleaning to
18,670 validated lines, 1,984 customers,
61 products, 36 months, ₹6.01 Cr of delivered
revenue.

I segment customers two independent ways — RFM rules and K-Means — estimate
their value, predict next-quarter revenue and forecast company revenue six
months ahead. Everything is reconciled in SQL and delivered through Power BI
and a Streamlit application.

The main finding is concentration: the top 20% of customers carry
64.33% of revenue, and both segmentation methods identify the same
group."

---

## 3 minutes

"Let me start with the problem. Businesses report revenue in aggregate but take
decisions at customer level. A monthly total cannot tell you whether the month
was carried by a few large customers or built on a broad base — so it cannot
tell you where to spend retention effort.

**The data.** It is synthetic, generated with seed 42 for academic
demonstration — it describes no real company. 18,819 raw order lines,
18,670 after cleaning, 1,984 purchasing customers,
61 products across 6 categories,
5 regions, from 01 January 2023 to 31 December 2025.

**Cleaning.** Every business rule is evaluated on the raw extract, the failing
rows are logged, a treatment is applied, and the rule is re-evaluated.
941 rows failed at least one rule before treatment; zero fail
after.

**Analysis.** Delivered revenue is ₹6.01 Cr at 23.35% margin. The
business grew 51.4% then 37.7% while margin rose —
so growth is not being bought with margin. And value is concentrated: the top
20% of customers produce 64.33%.

**Segmentation.** I scored every customer on recency, frequency and monetary
value into 11 rule-based segments, then clustered the same
features with K-Means at K = 4 — chosen by three rules I fixed before
seeing any results. The two methods agree on the high-value group with an
Adjusted Rand Index of 0.3952, which is stronger evidence than either alone.

**Prediction and forecasting.** These are different tasks. Customer-level
prediction reached a test R² of 0.0557 — better than every baseline but
weak, because 53.0% of customer-quarters have no order at all. I
report that honestly. Company-level forecasting works much better: a
Theta: Theta (seasonality auto-tested) model with a backtest mean error of 14.56%,
projecting ₹1.58 Cr over six months with an 80% interval.

**Delivery.** 57 SQL queries reproduce the metrics
independently, a Power BI model carries 84 DAX measures, and a
12-page Streamlit application loads the real trained models.

The practical output is a short list: the top decile, and the 52
high-value customers who have not ordered in 180 days."

---

## 5 minutes

*(Use the 3-minute script, then add these four blocks.)*

"**On data quality specifically.** The generator deliberately injects the
defects a real extract carries — missing values, non-ISO dates, numbers stored
as text, out-of-range discounts, invalid category labels, duplicates — and logs
every injection. That gives me a known ground truth to audit the cleaning
against, which real data could not. 149 duplicates removed,
28 engineered columns added, and every rule returns zero
afterwards.

**On why two segmentations.** RFM imposes boundaries I chose; K-Means finds
whatever grouping is actually in the data. Where they agree — the high-value
group — that is real structure. Where they disagree, in the middle of the base,
that tells me my rule boundaries are arbitrary there. Reporting both is more
informative than reporting either.

**On customer value.** I keep two quantities strictly separate. Historical
value is measured: ₹1.40 Cr of profit already earned. Forward value is
estimated by a random forest, R² 0.2705 but Spearman
0.4869 — it ranks customers much better than it predicts their
exact spend, so I use it to order a queue of attention, not to promise a
number.

**On the honest result.** The weakest part of the project is customer-level
prediction, and I would rather explain it than dress it up. It beats every
baseline, its total bias is only 1.12% so aggregates are usable, but
it explains almost none of the variance in individual outcomes. The cause is
structural zero-inflation, and the correct fix — a two-stage model — is in my
future scope rather than claimed as done."

---

## 10 minutes

*(Follow the 15-section plan in `outputs/final_audit/live_demo_plan.md` at its
compressed running order. Speak the 5-minute script as your narration while you
move through the application: Executive Overview during the EDA block,
Customer Segmentation during segmentation and CLV, Revenue Prediction and
Sales Forecast during the modelling block, Data Explorer at the end.)*

Two lines to have ready verbatim:

- Entering the Power BI section: "Power BI Desktop is a Windows application and
  wasn't available in my build environment, so what you're seeing is a design
  mockup rendered from the real data — not a screenshot. What is complete and
  validated is the semantic model and all 84 DAX measures,
  48 of 48 of which match their SQL equivalents."
- Entering the prediction section: "This is the weakest result in the project,
  and I'd like to explain why rather than skip it."

---

## 15 minutes

*(The full plan in `outputs/final_audit/live_demo_plan.md`, section by section,
with the timings given there. Use the 5-minute script as your spine and expand
each section with the numbers listed against it.)*

**Opening line:** "Good morning. I'm Swagata Das, MBA Data Science and AI at
Apex Institute of Management. I'll show you a customer revenue intelligence
platform I built during my internship at Tutorsuite Technologies — and I'll
start by saying the dataset is synthetic, generated for academic
demonstration."

**Closing line:** "So: raw transactions in, business decisions out, with every
number traceable to the file that produced it and every model chosen by a rule
fixed before I saw the results. Where the results were weak, I've reported them
as weak. I'm happy to take questions — and the application is still running if
you'd like to see anything again."

---

## Delivery notes

- **Pace.** Two sentences, then pause. Examiners interrupt; leave them room.
- **Pointing.** Say the number, then point at it. Not the reverse.
- **The synthetic-data line comes early,** in your own words, not in answer to
  a challenge.
- **When you don't know:** "That value was not directly measured in this
  project." An honest gap costs one mark; a fabricated figure that gets checked
  costs the viva.
- **If asked something covered later:** "I'm coming to that in two minutes — or
  I can jump there now if you'd prefer."
