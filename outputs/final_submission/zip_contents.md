# ZIP Contents

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

**Intended archive:** `Customer_Revenue_Intelligence_Final_Submission.zip`

## What goes in

| Folder | Files |
|---|---|
| `01_REPORT/` | 3 |
| `02_PRESENTATION/` | 2 |
| `03_SOURCE_CODE/` | 53 |
| `04_DATA/` | 16 |
| `05_SQL/` | 5 |
| `06_MODELS/` | 12 |
| `07_DASHBOARDS/` | 66 |
| `08_SCREENSHOTS/` | 81 |
| `09_VIVA/` | 32 |
| `10_DOCUMENTATION/` | 25 |
| `11_OUTPUT_TABLES/` | 238 |
| `SUBMISSION_README.md` | 1 |

**Total: 534 files, about
98 MB uncompressed.**

## Structure

```
Customer_Revenue_Intelligence_Final_Submission.zip
└── FINAL_SUBMISSION/
    │
    ├── SUBMISSION_README.md            ← read this first
    │
    ├── 01_REPORT/
    │   ├── Final_Internship_Report.docx
    │   ├── Final_Internship_Report.pdf
    │   └── report_validation_checklist.md
    │
    ├── 02_PRESENTATION/
    │   ├── Final_Internship_Presentation.pptx
    │   └── Final_Internship_Presentation.pdf
    │
    ├── 03_SOURCE_CODE/
    │   ├── app.py, config.py
    │   ├── src/          (14 modules)
    │   ├── pages/        (12 Streamlit pages)
    │   ├── notebooks/    (9 executed notebooks)
    │   ├── scripts/      (13 scripts)
    │   ├── tests/
    │   ├── assets/css/
    │   └── .streamlit/config.toml
    │
    ├── 04_DATA/
    │   ├── raw/          (generated extract + injection log)
    │   ├── processed/    (cleaned data and stage outputs)
    │   └── customer_revenue_intelligence.db
    │
    ├── 05_SQL/           (5 files)
    │
    ├── 06_MODELS/        (8 .pkl + 4 metadata)
    │
    ├── 07_DASHBOARDS/
    │   ├── PowerBI/      (model, DAX, M scripts, theme, build guide,
    │   │                  validation, page_design_mockups/)
    │   └── Streamlit/    (12 real screenshots, testing report, documentation)
    │
    ├── 08_SCREENSHOTS/   (81 numbered images, demo order)
    │
    ├── 09_VIVA/          (32 documents)
    │
    ├── 10_DOCUMENTATION/
    │   ├── README.md, requirements.txt, LICENSE, gitignore.txt
    │   ├── reproducibility_guide.md, user_manual.md
    │   ├── project_build_log.md, STEP2/STEP3 design notes
    │   ├── methodology_reports/   (9 reports)
    │   └── project_audits/        (8 audit documents)
    │
    └── 11_OUTPUT_TABLES/  (181 CSVs + report_facts.json)
```

## Removed before packaging

`scripts/build_submission.py` cleans these from the working project, and the
packaging step skips them:

| Removed | Why |
|---|---|
| `__pycache__/` | Compiled bytecode, regenerated automatically |
| `*.pyc`, `*.pyo` | Same |
| `.ipynb_checkpoints/` | Jupyter autosaves |
| `.pytest_cache/` | Test-runner cache |
| `work/`, `.report_build/`, `outputs/reports/_build/` | Build scratch |
| `~$*.docx`, `~$*.pptx` | Office lock files |

**Nothing required to reproduce the project is removed.** The data, the models,
the notebooks with their outputs and every source file are all included.

## Deliberately not duplicated

`outputs/figures/` holds 144 figures (26 MB).
The curated, numbered subset an examiner needs is already in
`08_SCREENSHOTS/` (81 images), so the full figure directory is **not** copied
into the package — it stays at `outputs/figures/` in the project folder and in
the GitHub repository.

## Creating the ZIP

```bash
cd customer-revenue-intelligence
python scripts/build_submission.py          # rebuilds the package and cleans caches

cd ..
zip -r Customer_Revenue_Intelligence_Final_Submission.zip \
    customer-revenue-intelligence/FINAL_SUBMISSION \
    -x "*__pycache__*" "*.ipynb_checkpoints*" "*.pyc"
```

On Windows, right-click the `FINAL_SUBMISSION` folder → **Send to → Compressed
(zipped) folder**, then rename it.

**Then open the ZIP and check that the report and the PPT are inside and open
correctly.** An archive you have not opened is not a deliverable.
