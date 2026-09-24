# Backup Manifest

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

## What must be backed up

| # | Item | Location in the project | Size | Regenerable? |
|---|---|---|---|---|
| 1 | Final report (`.docx` + `.pdf`) | `outputs/reports/` | 4.9 MB | Yes, by `scripts/build_report.py` |
| 2 | Final presentation (`.pptx` + `.pdf`) | `outputs/presentation/` | 5.2 MB | Yes, by `scripts/build_presentation.py` |
| 3 | Source code | `app.py`, `config.py`, `src/`, `pages/`, `scripts/`, `tests/` | 3.3 MB | **No — irreplaceable** |
| 4 | Notebooks | `notebooks/` | 29.8 MB | Only by re-executing |
| 5 | SQL scripts | `sql/` | 0.1 MB | **No — irreplaceable** |
| 6 | Datasets | `data/raw/`, `data/processed/`, `data/*.db` | 21.2 MB | Yes, from seed 42 |
| 7 | Trained models | `models/` | 5.4 MB | Yes, by re-running the pipeline |
| 8 | Screenshots and figures | `outputs/screenshots/`, `outputs/figures/` | 42.3 MB | Yes |
| 9 | Viva material | `outputs/viva/` (32 files) | 0.3 MB | Yes, by `scripts/build_viva.py` and `build_demo.py` |
| 10 | Documentation and audits | `README.md`, `docs/`, `outputs/final_audit/`, `outputs/final_submission/` | 0.2 MB | Yes |
| 11 | Power BI artefacts | `powerbi/` | 3.8 MB | Yes, by `run_powerbi_prep()` |
| 12 | Configuration | `requirements.txt`, `.gitignore`, `LICENSE`, `.streamlit/` | < 0.1 MB | **No — irreplaceable** |

**Total project size: about 120 MB** (excluding the
`FINAL_SUBMISSION/` package, which is hard-linked and adds no disk).

The four rows marked irreplaceable are the ones that matter. Everything else
can be regenerated, but only if the code survives.

## Recommended backup locations — use at least three

| # | Location | What to put there | Why |
|---|---|---|---|
| 1 | **Local computer** | The whole project folder | Your working copy. Not a backup on its own — one disk failure loses it |
| 2 | **External drive / USB** | `Customer_Revenue_Intelligence_Final_Submission.zip` | Offline copy, immune to account problems. Carry it to the viva |
| 3 | **Cloud storage** (Google Drive, OneDrive) | The same ZIP, plus the report and PPT as loose files | Accessible from any machine if your laptop fails on the day |
| 4 | **GitHub repository** | The whole repository, pushed | Version history and a shareable portfolio link |

**Carry the ZIP on a USB stick to the viva.** If your laptop fails, an examiner
can open the report and the PPT from any machine.

## What must NOT be backed up to a public location

| Item | Status in this project |
|---|---|
| Passwords, API keys, tokens | **None exist.** A repository-wide scan returns no matches |
| `.env` files, credentials, service-account keys | **None exist** |
| Real customer data | **None exists** — the dataset is synthetic |
| Personal documents (ID, certificates beyond the bonafide) | Not in the repository; keep them out |

The bonafide certificate details (name, guide, organisation) are on the report
title page by design — that is the document's purpose.

## Files too large for convenient GitHub use

None block a push. The largest single file is
`notebooks/02_exploratory_data_analysis.ipynb` at about
7.8 MB, well under
GitHub's 100 MB limit, so `git push` works and Git LFS is unnecessary.

If you want a slimmer public repository, uncomment the marked block at the end
of `.gitignore` to exclude `data/processed/`, `data/*.db`, `models/*.pkl` and
`outputs/figures/`. Everything excluded is regenerable from seed 42.
**Do not do this for the university copy** — the evaluator should be able to
open everything without running anything.

## Backup routine before submission

```bash
# 1. clean caches and build the package
python scripts/build_submission.py

# 2. create the ZIP (from the project's parent folder)
cd ..
zip -r Customer_Revenue_Intelligence_Final_Submission.zip \
    customer-revenue-intelligence/FINAL_SUBMISSION \
    -x "*__pycache__*" "*.ipynb_checkpoints*" "*.pyc"

# 3. copy the ZIP to the external drive and to cloud storage
# 4. push to GitHub (see github_final_check.md)
```

Verify each copy opens before you rely on it. A backup you have not tested is
not a backup.
