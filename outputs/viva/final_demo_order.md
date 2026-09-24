# Final Demonstration Order

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

## The order, and why it is this order

The sequence follows the **data's journey**, not the project's chapter list.
Each step answers the question the previous step raises, so the examiner is
never asked to hold an unexplained result in their head.

| # | Section | Surface to use | Time | The one number |
|---|---|---|---|---|
| 1 | Introduction | PPT slide 1 | 45 s | — |
| 2 | Business problem | PPT slide 2 | 1 min | Top 20% = 64.33% of revenue |
| 3 | Dataset | Screenshots 01–02 | 1 min | 18,670 lines, synthetic |
| 4 | Data cleaning | Screenshots 03–05 | 1 min | 941 rows failing → 0 |
| 5 | EDA | Streamlit: Executive Overview, Revenue Intelligence | 2 min | ₹6.01 Cr at 23.35% |
| 6 | RFM | Streamlit: Customer Segmentation | 1 min 30 s | Champions 53.83% of revenue |
| 7 | K-Means | Same page, cluster view | 1 min 30 s | K = 4, ARI 0.3952 |
| 8 | Customer value | Same page, value view | 1 min 30 s | 52 at-risk, ₹26.51 L |
| 9 | Revenue prediction | Streamlit: Revenue Prediction | 1 min 30 s | R² 0.0557 — say "weak" |
| 10 | Forecasting | Streamlit: Sales Forecast | 1 min 30 s | 14.56% backtest MAPE |
| 11 | SQL | Terminal, reconciliation query | 1 min | Returns exactly ₹6.01 Cr |
| 12 | Power BI | Screenshot 58 (mockup) | 1 min | 48/48 validated |
| 13 | Streamlit as a whole | Data Explorer + a CSV download | 2 min | 40/40 tests |
| 14 | Recommendations | Streamlit: Business Recommendations | 1 min | 18 evidence-linked |
| 15 | Conclusion | PPT slide 20 | 45 s | 135 checks, 134 pass |

**Total: 15 minutes.**

## Two adjustments to the "recommended" order, and why

1. **RFM, K-Means and customer value run back-to-back on one Streamlit page**
   (steps 6–8), because the application already presents them together. Jumping
   between surfaces for three related results breaks the thread.
2. **SQL comes after prediction and forecasting** (step 11), not before Power
   BI in the abstract. By that point the examiner has seen the numbers, so the
   reconciliation lands as *"and here is the independent proof those figures
   are right"* rather than as an unmotivated database tour.

## If you get 10 minutes

Drop steps 6, 11 and 14; fold RFM into step 7 in one sentence. Running order:
1 → 2 → 3 → 4 → 5 → 7 → 8 → 9 → 10 → 13 → 15.

## If you get 5 minutes

Steps 1, 2, 5, 7, 9, 10, 15 — and say the synthetic-data line in step 1.

## If you are told "just show me it working"

Open the application and go: Executive Overview → Customer Segmentation (switch
on the at-risk filter) → Sales Forecast (switch 80% to 95%) → Data Explorer
(download a CSV). Four screens, two minutes, and every one of them is live.

## Transitions worth rehearsing

- **Cleaning → EDA:** "With the data validated, here's what it actually says."
- **EDA → RFM:** "Revenue is concentrated — so the next question is *in whom*."
- **RFM → K-Means:** "Those are my rules. Here's what happens when I let an
  algorithm find the groups instead."
- **K-Means → CLV:** "Both methods agree on who is valuable. The next question
  is whether they'll stay valuable."
- **CLV → Prediction:** "That's the next twelve months at customer level. This
  is the next quarter — and it's the weakest result in the project."
- **Prediction → Forecasting:** "Individual customers are hard to predict. The
  company total is a different matter."
- **Forecasting → SQL:** "Every number you've seen was computed in Python. Here
  it is again, computed independently in SQL."
- **SQL → Power BI:** "That's the reconciliation. Here's how a manager would
  actually consume it — and I need to be clear about what this image is."

## Close

"So: raw transactions in, business decisions out, with every number traceable
to the file that produced it and every model chosen by a rule fixed before I
saw the results. Where the results were weak, I've reported them as weak. I'm
happy to take questions — and the application is still running if you'd like to
see anything again."
