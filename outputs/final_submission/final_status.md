# Final Project Status

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

| Area | Status | Reason |
|------|--------|--------|
| Report | READY AFTER MANUAL ACTION | 40 pages, university format, all 20 required sections present, 32-item validation passed. You must fill the UID and sign the certificate |
| PPT | READY AFTER MANUAL ACTION | 22 slides on the university template with speaker notes; no placeholder text remains. You must fill the UID on slide 1 |
| Python | READY | 41 modules, 30,690 lines, pyflakes clean; all nine pipeline entry points import-tested in this environment |
| SQL | READY | 11 tables, 2 views, 57 queries; 56/56 validation and 20 data-quality checks pass |
| ML | READY | Four models persisted with metadata; every one selected by a rule fixed in advance. The weak result (prediction R² 0.0557) is reported as weak rather than replaced |
| Power BI | READY AFTER MANUAL ACTION | Semantic model, 84 DAX measures (48/48 validated against SQL), M scripts, theme and build guide are complete. The .pbix itself needs a Windows machine — the nine page layouts are labelled design mockups until then |
| Streamlit | READY | 12 pages, 40/40 headless tests pass, 12 real screenshots captured |
| GitHub | READY AFTER MANUAL ACTION | README, requirements, .gitignore and LICENSE finalised; no secrets; 16/16 readiness checks pass. You must run the push |
| Viva | READY | 32 documents, 319 questions, three mock vivas, a six-length demo script, demo order and failure handling |
| Backup | READY AFTER MANUAL ACTION | The package is assembled and the routine is documented. Creating the ZIP and copying it to USB, cloud and GitHub are yours |
| Data | READY | 18,819 raw → 18,670 clean lines; every business rule returns zero failures; synthetic status declared in every document |
| Documentation | READY | README, reproducibility guide, user manual, build log, Power BI build guide, 9 methodology reports, 8 audit documents, 12 submission documents |
| Reproducibility | READY | Fixed seed 42; 135 automated checks, 134 pass, 0 fail; every stage's entry point and output verified |

**8 READY · 5 READY AFTER MANUAL ACTION · 0 NEEDS TECHNICAL
FIX · 0 MISSING.**

## What this means

**Nothing is missing and nothing needs a technical fix.** Every area is either
finished or waiting on a task only you can do — filling your UID, signing the
certificate, running the Git push, creating the backups, and optionally
building the `.pbix` on a Windows machine.

The five areas marked *READY AFTER MANUAL ACTION* are not incomplete work.
They are:

| Area | What is waiting |
|---|---|
| Report | Your UID; your signature |
| PPT | Your UID |
| Power BI | A Windows machine — everything buildable without one is built and validated |
| GitHub | Your credentials and your push |
| Backup | Your USB, your cloud account |

## No numerical score is assigned

This is a readiness assessment, not a quality ranking. The evidence for each
status is in `outputs/final_audit/project_audit.md` (16 components),
`MASTER_SUBMISSION_CHECKLIST.md` and this package's other documents.
