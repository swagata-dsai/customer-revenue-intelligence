# GitHub Upload Report

*Generated 2026-09-24. Every line below is the actual result of a command run
in this environment. Nothing is assumed and nothing is predicted.*

---

## Outcome in one line

**The repository was fully prepared and committed locally, but the push did NOT
happen.** This session's GitHub credential is not authorised for the target
repository, and the push was stopped rather than worked around.

---

## Report fields

| Field | Actual value |
|---|---|
| **GitHub username** | `swagata-dsai` (verified via `GET /user`: name "Swagata Das", email `swagataofficial07@gmail.com` — your account, confirmed before anything was attempted) |
| **Repository** | `customer-revenue-intelligence` |
| **Branch** | `main` |
| **Remote** | `origin` → `https://github.com/swagata-dsai/customer-revenue-intelligence.git` |
| **Commit** | `b3382a8fc5b59cb9f515b386bf424c60fb738379` — "Final Customer Revenue Intelligence project" |
| **Files committed** | 678 files |
| **Committed size** | ~115 MB |
| **Security checks** | **PASS** |
| **README** | **PASS** |
| **Requirements** | **PASS** |
| **GitHub push** | **FAILED — blocked by session credential policy. Not attempted with any workaround.** |
| **Repository URL** | Not yet created/published. Intended: `https://github.com/swagata-dsai/customer-revenue-intelligence` |

---

## Why the push did not happen

Two independent blocks, both from the platform this session runs inside — not
from your GitHub account, and not from anything wrong with the project:

**1. The git proxy refuses to supply a credential for this repository.**

```
$ git push --dry-run origin main
remote: access denied by the git proxy: swagata-dsai/customer-revenue-intelligence
is not in this session's authorized repository set, so the proxy will not inject
a credential for it. To fix, add the repository to the session's sources.
fatal: unable to access '...': The requested URL returned error: 403
```

**2. The GitHub API refuses repository creation from this session.**

```
$ POST https://api.github.com/user/repos
{"message":"This GitHub API path is not available: sessions are bound to their
configured repositories. Use repository-scoped endpoints (repos/{owner}/{repo}/...)."}
```

The session token authenticates as you and can read `/user`, but it is scoped
to repositories explicitly attached to the session. `customer-revenue-intelligence`
is not attached, so neither creating it nor pushing to it is permitted.

**What was NOT done, deliberately:** no force push, no alternative credential,
no different account, no push to any other repository, and no claim of success.

---

## Whether the repository already exists on your account

**Unknown — and deliberately not guessed.** The API call that would answer this
(`GET /repos/swagata-dsai/customer-revenue-intelligence`) is blocked by the same
session scoping. Nothing was inspected, modified or deleted on your account.

If the repository does already exist and contains commits, follow the "existing
repository" path in the instructions below rather than pushing blind.

---

## Files committed (678)

| Area | Files | Notes |
|---|---|---|
| `outputs/` | 541 | figures, tables, reports, screenshots, viva pack, audit documents |
| `powerbi/` | 40 | semantic model, DAX measures, M scripts, theme, build guide |
| `data/` | 16 | raw + processed CSVs and the SQLite database |
| `src/` | 14 | the pipeline modules |
| `scripts/` | 13 | dataset generation, builders, project audit |
| `pages/` | 12 | Streamlit pages |
| `models/` | 12 | trained model artefacts and metadata |
| `notebooks/` | 9 | executed, with outputs saved |
| `sql/` | 5 | schema and analysis queries |
| `docs/` | 4 | reproducibility guide, build log, methodology |
| `assets/` | 4 | CSS and images |
| `tests/` | 1 | Streamlit test suite |
| Root | 7 | `app.py`, `config.py`, `README.md`, `requirements.txt`, `.gitignore`, `LICENSE`, `.streamlit/config.toml` |

Largest committed files — all far under GitHub's 100 MB per-file limit, so no
Git LFS is required:

| File | Size |
|---|---|
| `notebooks/02_exploratory_data_analysis.ipynb` | 7.5 MB |
| `data/processed/customer_sales_cleaned.csv` | 6.3 MB |
| `data/customer_revenue_intelligence.db` | 5.3 MB |
| `models/clv_model.pkl` | 5.1 MB |
| `notebooks/09_powerbi_data_model.ipynb` | 4.2 MB |

---

## Files intentionally excluded

| Excluded | Why |
|---|---|
| `FINAL_SUBMISSION/` | A hard-linked **mirror** of files already tracked elsewhere in the repository. Committing it would roughly double repository size while adding zero new content. Rebuilt on demand with `python scripts/build_submission.py`. |
| `__pycache__/`, `*.pyc` | Build artefacts |
| `.env`, `*.env`, `*.pem`, `*.key`, `secrets.toml`, `credentials.json` | Credential patterns — ignored as a precaution; **none of these files exist in the project** |
| `venv/`, `.venv/`, `env/` | Virtual environments |
| `.ipynb_checkpoints/`, `.pytest_cache/`, `.coverage` | Tooling caches |
| `.idea/`, `.vscode/`, `.DS_Store`, `~$*.docx`, `~$*.pptx` | Editor and OS noise |

**Nothing required to reproduce the project was excluded.** The dataset, the
cleaned data, the database, the trained models, the executed notebooks and
every output figure and table are all committed.

---

## Security check — PASS

| Check | Result |
|---|---|
| `.env` / `*.env` files present | **None found** |
| Private keys (`*.pem`, `*.key`, `id_rsa*`) | **None found** |
| Certificate stores (`*.p12`, `*.pfx`) | **None found** |
| Files named `*credential*`, `*secret*`, `*token*` | **None found** |
| Content scan for `api_key`, `secret_key`, `access_token`, `password`, `bearer`, AWS `AKIA…`, GitHub `ghp_…` / `github_pat_…`, OpenAI `sk-…`, `BEGIN PRIVATE KEY` across all `.py`, `.ipynb`, `.sql`, `.toml`, `.json`, `.yaml`, `.md`, `.txt` files | **1 match, benign** — a line of prose in `scripts/build_submission.py` that *describes* this very scan. No assignment, no value. |
| `.streamlit/config.toml` | Theme and server settings only — no `secrets.toml` exists |
| GitHub token exposure | The session token was never written to any file, never committed, and is not printed in this report |
| Personal data in the dataset | `Customer_Name` values (e.g. "Tanvi Mishra") are **synthetically generated** by `scripts/generate_dataset.py` with seed 42. They are not real people. Every analytical output uses `Customer_ID` only. |

---

## README — PASS

`README.md`, 27 KB, regenerated from `outputs/tables/report_facts.json` so every
number in it is the project's actual measured value. All requested sections are
present:

Project Overview · Business Problem · Objectives · Key Features · Technology
Stack · Project Architecture · Dataset · Methodology · Machine Learning ·
RFM Analysis · Customer Segmentation · CLV · Revenue Prediction · Sales
Forecasting · SQL Analytics · Power BI Dashboard · Streamlit Application ·
Project Screenshots · Installation · How to Run · Notebook Execution Order ·
Project Structure · Key Findings · Business Recommendations · Limitations ·
Future Scope · Reproducibility · Academic Disclaimer · Licence

Badges added: Python 3.11, Streamlit, scikit-learn, SQLite, MIT licence.

The synthetic-data warning appears in the first screen of the README:

> ⚠️ **The dataset in this repository is synthetic.** It is generated by
> `scripts/generate_dataset.py` with a fixed seed (42) for academic
> demonstration. It does not represent any real company, customer or
> transaction, including the internship host organisation.

The weak prediction result (R² 0.0557) is stated as weak in the README rather
than omitted or dressed up.

---

## Requirements — PASS

`requirements.txt` was checked against the **actual imports** in every `.py`
file (AST parse of `src/`, `pages/`, `scripts/`, `tests/`, `app.py`,
`config.py`). Every third-party import is covered:

`pandas` · `numpy` · `scipy` · `scikit-learn` · `statsmodels` · `joblib` ·
`matplotlib` · `seaborn` · `plotly` · `streamlit` · `jupyter` · `python-docx` ·
`python-pptx` · `pypdf` · `Pillow`

Dependency resolution verified:

```
$ pip install --dry-run -r requirements.txt
exit=0
```

---

## Local git state (ready to push)

```
branch:  main
commit:  b3382a8  Final Customer Revenue Intelligence project
remote:  origin  https://github.com/swagata-dsai/customer-revenue-intelligence.git
status:  clean — no untracked or modified files
```

The repository is complete and staged. The only missing step is the push, which
requires credentials this session is not permitted to use.

---

## What you need to do

### Option A — authorise this session (fastest, I finish the job)

Add `swagata-dsai/customer-revenue-intelligence` to this conversation's GitHub
sources, then tell me. I will create the repository if it does not exist, push
`main`, set the description and topics, and verify the result.

### Option B — push it yourself

Download the project, then from its folder run:

```bash
# 1. Create the repository on github.com/new
#    Name:        customer-revenue-intelligence
#    Visibility:  Public
#    Do NOT tick "Add a README", ".gitignore" or "Choose a licence"
#    (the repository already contains all three)

# 2. Push
git remote -v                      # confirm origin points at your account
git push -u origin main
```

If the repository **already exists and has commits**, do not force push. Run
this first and read the output before doing anything else:

```bash
git fetch origin
git log --oneline origin/main -10   # what is already there
git log --oneline main -1           # what you are adding
```

Then merge rather than overwrite:

```bash
git pull --rebase origin main
git push -u origin main
```

### Then set the description and topics

On the repository page → **About** (gear icon, top right):

**Description:**
```
End-to-end MBA Data Science project for customer segmentation, revenue intelligence, CLV analysis, revenue prediction, sales forecasting, SQL analytics, Power BI and Streamlit.
```

**Topics:**
```
python  data-science  machine-learning  customer-segmentation  rfm-analysis
clv  revenue-prediction  sales-forecasting  sql  power-bi  streamlit  mba-project
```

### Then verify

- Repository owner reads `swagata-dsai`
- Branch is `main`
- README renders with the badges and the synthetic-data warning
- `src/`, `pages/`, `notebooks/`, `sql/` are all visible
- `requirements.txt` and `.gitignore` are present
- No `.env` file and no `FINAL_SUBMISSION/` folder appear

---

## Authentication note

Your GitHub identity was verified read-only, once, to confirm the target
account was yours before any write was attempted. No password was requested, no
token was stored in the project, and no token value appears anywhere in this
repository or in this report.
