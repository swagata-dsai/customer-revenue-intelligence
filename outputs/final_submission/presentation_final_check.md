# Presentation — Final Check

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

**File:** `outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx` (and `.pdf`)
**Extent:** 22 slides · 9 images · 8 tables · speaker notes on **every** slide
**Template:** built on the university-supplied template
(`assets/templates/summer_internship_template.pptx`) — its layouts, colours,
fonts, logos, slide numbering and Thank-You slide are unchanged; only the
placeholder text was replaced.

| # | Slide | Present | Notes |
|---|-------|---------|-------|
| 1 | Title | Yes | Candidate and guide from the certificate; `[TO BE FILLED]` UID — [TO BE FILLED BY STUDENT] |
| 2 | Introduction | Yes | Six points framing the business problem |
| 3 | About the organisation | Yes | Internship details plus the explicit synthetic-data statement |
| 4 | About the topic | Yes | Pipeline diagram: customer data to business decisions |
| 5 | Literature review | Yes | Six strands with a comparison table; real citations only |
| 6 | Research gap | Yes | The gap and the integrated solution; no novelty over-claimed |
| 7 | Objectives | Yes | Eleven numbered objectives, all implemented |
| 8 | Research methodology | Yes | Implementation flowchart with the three validation gates |
| 9 | Dataset and preprocessing | Yes | Dataset table and the before/after rule table on one slide |
| 10 | EDA | Yes | Monthly revenue trend and category revenue vs profit |
| 11 | RFM and K-Means | Yes | Both segmentations on one slide, with their agreement |
| 12 | CLV | Yes | Historical vs estimated forward value; model comparison table |
| 13 | Revenue prediction | Yes | Model comparison; R² 0.0557 stated as weak |
| 14 | Sales forecasting | Yes | Forecast chart with prediction intervals |
| 15 | SQL | Yes | Database stats, techniques and six findings computed in SQL |
| 16 | Power BI | Yes | Labelled design mockup, with the reason stated on the slide |
| 17 | Streamlit | Yes | Real screenshot of the running application |
| 18 | Findings and recommendations | Yes | Six findings with implication and recommendation |
| 19 | Future scope | Yes | Six directions, each answering a stated limitation |
| 20 | Conclusion | Yes | Four closing points |
| 21 | References | Yes | Eleven of the 38 report references |
| 22 | Thank You | Yes | Questions and discussion, with candidate and title |

**All 22 slides present.** Two sections named in the generic checklist —
"data preprocessing" and "recommendations" — are combined with their
neighbours (slides 9 and 18) because the content belongs together; nothing is
omitted.

## Quality checks performed

| Check | Result |
|---|---|
| Placeholder text removed | Verified — a grep for `Sample text here`, `About Company`, `YOUR TITLE WRITE HERE`, `TOPIC OF PRESENTATION` and `Font size 24` returns nothing |
| File validation | Passes `validate.py` against the original template baseline |
| Charts readable | All 22 slides rendered at 100 dpi and inspected; no overflow, no text through shapes |
| Screenshots readable | The Streamlit screenshot and the Power BI mockup are full-width on their slides |
| Numbers match the report | Every figure is read from the same fact pack the report uses |
| Speaker notes | 22/22 slides carry notes written for the viva, not a repeat of the slide text |

## Still to complete

| Item | Where | Action |
|---|---|---|
| UID | Slide 1, `[TO BE FILLED]` | [TO BE FILLED BY STUDENT] |
| Internship year | Slide 1 — the certificate does not print one | [TO BE FILLED BY STUDENT] if wanted |
| Spelling read-through | Whole deck | Read once yourself; no automated spell-check was run |
