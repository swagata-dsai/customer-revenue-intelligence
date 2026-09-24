# Final Submission Checklist

*Generated 2026-09-24 by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*

A box is ticked only where the item was verified in the generated artefact.

## A. University report

`outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx`
and `.pdf` — 40 pages, A4, Times New Roman, body 12 pt / 1.5 / justified.

- [x] Final report completed — 40 pages, 9 figures, 16 tables, 38 references
- [x] Title page — candidate, programme, semester, guide, institute, university, CU logo
- [x] Certificate — reproduces the wording of the issued bonafide certificate; signature lines left blank
- [ ] **Declaration** — not included. The supplied university format does not contain one. Add it if your department requires it.
- [x] Acknowledgement — names the internship organisation and the guide
- [x] Abstract — one page, states the dataset is synthetic
- [x] Table of contents — page numbers resolved from the rendered PDF
- [x] List of figures — 9 entries, every one appears
- [x] List of tables — 16 entries, every one appears
- [x] Literature survey — Chapter 2, five areas plus a comparison table
- [x] Methodology — Chapter 3, twelve sections including design constraints and alternatives
- [x] Results — Chapter 4, eleven sections with validation
- [x] Findings — Section 4.12 with evidence and source per finding
- [x] Recommendations — Section 4.12, evidence-linked
- [x] Conclusion — Section 5.1
- [x] Future scope — Section 5.4
- [x] References — 38 entries, every one cited by a generated number
- [x] Appendix — model configuration and the reconciliation SQL
- [x] User manual — setup steps with verified commands and a page-by-page guide

**One field still to fill:** `[UID]` on the title page and in the
acknowledgement. The bonafide certificate does not print it.

## B. PPT

`outputs/presentation/Customer_Revenue_Intelligence_Summer_Internship_Presentation.pptx`
and `.pdf` — 22 slides on the university template, speaker notes on every slide.

- [x] Title slide (1) — [ ] `[TO BE FILLED]` UID still to complete
- [x] Introduction (2)
- [x] Company/organisation section (3)
- [x] Topic (4)
- [x] Literature review (5)
- [x] Research gap (6)
- [x] Objectives (7)
- [x] Methodology (8)
- [x] Dataset (9)
- [x] EDA (10)
- [x] RFM and K-Means (11)
- [x] CLV (12)
- [x] Prediction (13)
- [x] Forecasting (14)
- [x] SQL (15)
- [x] Power BI (16) — labelled as a design mockup
- [x] Streamlit (17) — real screenshot
- [x] Findings and recommendations (18)
- [x] Future scope (19)
- [x] Conclusion (20)
- [x] References (21)
- [x] Thank-you slide (22)

## C. Technical project

- [x] Dataset — 18,819 raw → 18,670 clean lines, seed 42
- [x] Cleaning — every business rule returns zero failures after treatment
- [x] EDA — ₹6.01 Cr revenue at 23.35% margin characterised across six dimensions
- [x] RFM — 1,984 customers, 11 segments
- [x] Segmentation — K = 4, silhouette 0.3534
- [x] CLV — historical ₹1.40 Cr measured; forward value R² 0.2705
- [x] Prediction — Linear regression, test R² 0.0557 (reported as weak)
- [x] Forecasting — Theta: Theta (seasonality auto-tested), backtest MAPE 14.56%
- [x] SQL — 11 tables, 57 queries, 56/56 checks pass
- [~] Power BI — model, 84 measures and build guide complete and validated; **.pbix not built** (Windows-only tool unavailable)
- [x] Streamlit — 12 pages, 40/40 tests pass

## D. GitHub

- [x] README — full structure, written for a reader who has never seen the project
- [x] requirements.txt — derived from an AST scan of the actual imports
- [x] .gitignore — professional, does not exclude evaluation artefacts
- [x] LICENSE — MIT
- [x] Source code — 41 modules, pyflakes clean
- [x] Notebooks — 9, executed, in order
- [x] SQL — 4 files plus the loader
- [x] Models — 8 artefacts with metadata
- [x] Documentation — reproducibility guide, build log, Power BI build guide

## E. Viva

`outputs/viva/` — 18 files, 319 questions.

- [x] Project introduction — 15 s / 30 s / 45 s / 1 min / 3 min scripts
- [x] Technical questions — 47 intermediate
- [x] ML questions — 30 advanced data science
- [x] SQL questions — 25, with examples against the real schema
- [x] Power BI questions — 25
- [x] Streamlit questions — 22
- [x] Business questions — 25
- [x] Limitations — covered in the master summary, revision sheet and Top 20
- [x] Future scope — clearly separated from completed work throughout

## Items requiring your action before submission

| # | Action | Where |
|---|---|---|
| 1 | Replace `[UID]` with your university ID | Report title page and acknowledgement |
| 2 | Replace `[TO BE FILLED]` with your UID | PPT slide 1 |
| 3 | Sign the certificate page | Printed report, page ii |
| 4 | Add a Declaration page if your department requires one | Report front matter |
| 5 | Confirm the internship year on the title page if the department wants it printed | Report and PPT |
| 6 | Optionally build the .pbix on a Windows machine | `powerbi/POWERBI_BUILD_GUIDE.md` |
