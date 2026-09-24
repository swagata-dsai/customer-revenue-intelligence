# GitHub Final Check

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

| Check | Status | Evidence |
|-------|--------|----------|
| Repository name | READY | `customer-revenue-intelligence` — matches the project folder and the README title |
| README | READY | Full structure: overview, objectives, architecture diagram, dataset, methodology, ML results, SQL, Power BI, Streamlit, installation, findings, limitations, future scope, academic disclaimer |
| .gitignore | READY | Excludes caches, virtualenvs, IDE files, secrets and scratch; documents what is deliberately kept for evaluation |
| requirements.txt | READY | Derived from an AST scan of every `.py` file and notebook; `pip install -r requirements.txt` dry-run verified |
| LICENSE | READY | MIT |
| Source code | READY | 41 modules, 30,690 lines, `pyflakes` clean |
| Notebooks | READY | 9 notebooks, executed with outputs saved, numbered in execution order |
| SQL | READY | `schema.sql`, `analysis_queries.sql`, `business_queries.sql`, `powerbi_views.sql`, `load_database.py` |
| Documentation | READY | `docs/reproducibility_guide.md`, `docs/project_build_log.md`, `powerbi/POWERBI_BUILD_GUIDE.md`, 13 methodology reports, 8 audit documents |
| Model files | READY | 8 `.pkl` artefacts with 4 metadata files recording library versions and selection rules |
| Dataset handling | READY | Committed by default so an evaluator can open everything; an optional exclusion block in `.gitignore` slims a public copy |
| No passwords | READY | Repository-wide scan for password/secret/api_key/token assignments returns no matches |
| No API keys | READY | No `.env`, no key files, no service-account JSON |
| No personal confidential information | READY | Dataset is synthetic; analytical outputs use `Customer_ID` only; the dataset preview image masks `Customer_Name` |
| No unnecessary temporary files | READY | `__pycache__`, `.ipynb_checkpoints`, `work/`, `.report_build/` and `_build/` removed before packaging |
| Runs from documented instructions | READY | All nine pipeline entry points import-tested; application passes 40/40; audit passes 134/135 |

**16 of 16 checks READY.**

## Exact Git commands

Run these from the project root. Nothing here is destructive.

```bash
# 1. see what will be committed
git status

# 2. first time only: initialise and set your identity
git init
git config user.name  "Swagata Das"
git config user.email "your.email@example.com"

# 3. stage and commit
git add .
git commit -m "Final internship project submission"

# 4. first time only: set the branch and the remote
git branch -M main
git remote add origin https://github.com/<your-username>/customer-revenue-intelligence.git

# 5. push
git push -u origin main
```

For later updates:

```bash
git add .
git commit -m "<describe what changed>"
git push
```

**Do not use `git push --force`, `git reset --hard` or `git clean -fdx`.** None
is needed here, and each can destroy work irreversibly.

## Before you push — 60-second check

```bash
git status --short | head -30              # anything unexpected staged?
grep -rIn "password\|api_key\|secret" --include=*.py . | head   # expect nothing
du -sh .                                   # about 120 MB
```

If `git status` lists files you did not expect — a virtual environment, a cache
directory — stop and check `.gitignore` before committing.

## Repository description and topics (optional, for a portfolio)

**Description:** *Customer analytics platform: RFM and K-Means segmentation,
customer lifetime value, revenue prediction and time-series forecasting, with
SQL reconciliation, a Power BI semantic model and a Streamlit application.
Synthetic dataset.*

**Topics:** `data-science` `customer-analytics` `rfm-analysis` `kmeans`
`clv` `forecasting` `streamlit` `power-bi` `sql` `python` `mba-project`

Say **synthetic dataset** in the description. It is accurate, and it prevents a
reader assuming the numbers are a real company's.
