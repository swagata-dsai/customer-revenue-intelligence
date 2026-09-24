# MASTER SUBMISSION CHECKLIST

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

`[x]` = verified in the generated artefact. `[ ]` = your action.
`[~]` = present with a documented qualification.

## A. REPORT

- [x] Final report — 40 pages, university format
- [x] PDF — `01_REPORT/Final_Internship_Report.pdf`
- [x] DOCX — `01_REPORT/Final_Internship_Report.docx`
- [x] Title page — candidate, programme, guide, institute, university, CU logo
- [x] Certificate — reproduces the issued bonafide certificate's wording
- [ ] **Declaration** — absent; the supplied format has none. Add only if required
- [x] Acknowledgement — names the organisation and the guide
- [x] Abstract — one page, states the data is synthetic
- [x] Table of Contents — all 180 page anchors resolve
- [x] List of Figures (9) and List of Tables (16)
- [x] Literature review — Chapter 2, five areas + comparison table
- [x] Methodology — Chapter 3, 12 sections
- [x] Results — Chapter 4, 12 sections with validation
- [x] Findings — Section 4.12, evidence-linked
- [x] Recommendations — Section 4.12
- [x] Conclusion — Section 5.1
- [x] Future scope — Section 5.4
- [x] References — 38, every one cited by a generated number
- [x] Appendix — model configuration and reconciliation SQL
- [x] User manual — commands import-tested
- [ ] **Fill `[UID]`** on the title page and in the acknowledgement
- [ ] **Sign the certificate page**

## B. PPT

- [x] PPTX — `02_PRESENTATION/Final_Internship_Presentation.pptx`
- [x] PDF — `02_PRESENTATION/Final_Internship_Presentation.pdf`
- [x] All required sections — 22 slides, every prescribed topic covered
- [x] Charts readable — all slides rendered and inspected; no overflow
- [x] Screenshots readable — full-width on their slides
- [x] No placeholder text — template placeholders verified absent by grep
- [x] Speaker notes on all 22 slides
- [ ] **Fill `[TO BE FILLED]` UID** on slide 1
- [ ] **Spelling read-through** — no automated spell-check was run

## C. CODE

- [x] Python — 41 modules, 30,690 lines, pyflakes clean
- [x] Notebooks — 9, executed with outputs saved
- [x] SQL — 4 files plus the loader
- [x] requirements.txt — AST-derived; install dry-run verified
- [x] .gitignore — professional; keeps evaluation artefacts
- [x] README — full structure with architecture diagram
- [x] LICENSE — MIT
- [x] Tests — 40/40 pass

## D. DATA

- [x] Dataset — `04_DATA/raw/` (18,819 lines, seed 42)
- [x] Processed dataset — `04_DATA/processed/` (18,670 lines)
- [x] Database — `04_DATA/customer_revenue_intelligence.db`
- [x] Data dictionary — report Section 3.2 and `docs/STEP2_Dataset_Design.md`
- [x] Academic disclaimer — README, cover page, `SUBMISSION_README.md`, report abstract
- [x] Injection log — `04_DATA/raw/data_quality_injection_log.json`

## E. MACHINE LEARNING

- [x] RFM — 1,984 customers, 11 segments
- [x] K-Means — K = 4, silhouette 0.3534, ARI vs RFM 0.3952
- [x] CLV — historical ₹1.40 Cr; forward model R² 0.2705
- [x] Revenue prediction — Linear regression, test R² 0.0557 *(weak, reported as weak)*
- [x] Forecasting — Theta: Theta (seasonality auto-tested), backtest MAPE 14.56%
- [x] Models — 8 `.pkl` with 4 metadata files
- [x] Evaluation — out-of-time splits, leakage audit, rolling-origin backtest

## F. DASHBOARDS

- [~] **Power BI** — model, 84 DAX measures
  (48/48 validated), M scripts, theme and build
  guide complete. **The `.pbix` is not built** — Desktop is Windows-only
- [x] Streamlit — 12 pages, 40/40 tests
- [x] Screenshots — 81 numbered images; 12 real Streamlit, 10 labelled mockups

## G. VIVA

- [x] Viva questions — 319 across 18 Step-16 documents
- [x] Answers — every one matched to the actual implementation
- [x] Live demo — plan, script (six lengths), demo order, failure handling
- [x] Rapid-fire — 50 + 55 questions across two files
- [x] Revision sheet — `09_VIVA/final_revision_sheet.md` and `last_minute_revision.md`
- [x] Demo scripts — Power BI, Streamlit, SQL, ML, business

## H. BACKUP

- [ ] **Local backup** — keep the project folder
- [ ] **External drive / USB** — carry the ZIP to the viva
- [ ] **Cloud backup** — ZIP plus loose report and PPT
- [ ] **GitHub** — `git push` (commands in `github_final_check.md`)
- [ ] **Final ZIP** — create it (`zip_contents.md`)

---

## Summary

| Category | Verified | Your action |
|---|---|---|
| A. Report | 20 items | Fill UID · sign certificate · Declaration if required |
| B. PPT | 7 items | Fill UID · spelling read-through |
| C. Code | 8 items | — |
| D. Data | 6 items | — |
| E. Machine learning | 7 items | — |
| F. Dashboards | 2 of 3 | Optional: build the `.pbix` on Windows |
| G. Viva | 6 items | Rehearse |
| H. Backup | 0 of 5 | All five are yours |
