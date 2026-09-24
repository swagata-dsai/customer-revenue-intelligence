# Reproducibility Guide

*Generated 2026-09-24 by `python scripts/build_packaging.py`. Every status is derived from the files actually on disk and from `outputs/tables/report_facts.json`.*

This guide assumes you have never seen the project. Following it from a clean
machine rebuilds every dataset, model, figure, table, report, slide deck and
viva document in this repository.

## 1. Python version

**Python 3.11.** The persisted models were written with scikit-learn 1.8.0 and
statsmodels 0.15.0; loading them under an older minor version may warn or fail.

```bash
python --version        # expect Python 3.11.x
```

## 2. Environment setup

```bash
git clone <repository-url>
cd customer-revenue-intelligence

python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

## 3. Dependency installation

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

To reproduce the saved models byte for byte rather than merely load them:

```bash
pip install scikit-learn==1.8.0 statsmodels==0.15.0
```

SQLite needs no installation — Python's built-in `sqlite3` is used.

## 4. Dataset generation

The repository already contains the generated data. To rebuild it from
nothing:

```bash
python scripts/generate_dataset.py     # writes data/raw/customer_sales_raw.csv
python scripts/validate_dataset.py     # checks it against the generator's ground truth
```

The seed is fixed at 42, so the output is identical every time:
18,819 raw order lines, 23 columns, plus
`data/raw/data_quality_injection_log.json` recording every defect deliberately
injected.

## 5. Pipeline execution order

Run these in order. Each stage reads only the persisted output of the one
before it, so a stage can be re-run on its own once its input exists.

```bash
python -c "from src.data_cleaning import run_pipeline;      run_pipeline()"
python -c "from src.eda import run_eda;                     run_eda()"
python -c "from src.rfm import run_rfm;                     run_rfm()"
python -c "from src.segmentation import run_segmentation;   run_segmentation()"
python -c "from src.clv import run_clv;                     run_clv()"
python -c "from src.prediction import run_prediction;       run_prediction()"
python -c "from src.forecasting import run_forecasting;     run_forecasting()"
python -c "from src.sql_analytics import run_sql_workflow;  run_sql_workflow()"
python -c "from src.powerbi_prep import run_powerbi_prep;   run_powerbi_prep()"
```

Every function name above was import-tested against the current source.

## 6. Notebook execution order

The notebooks narrate the same stages and are committed with their outputs. To
re-execute them:

```bash
jupyter lab      # or: jupyter notebook
```

| Order | Notebook |
|---|---|
| 1 | `notebooks/01_data_cleaning.ipynb` |
| 2 | `notebooks/02_exploratory_data_analysis.ipynb` |
| 3 | `notebooks/03_rfm_customer_analysis.ipynb` |
| 4 | `notebooks/04_kmeans_customer_segmentation.ipynb` |
| 5 | `notebooks/05_customer_lifetime_value.ipynb` |
| 6 | `notebooks/06_revenue_prediction.ipynb` |
| 7 | `notebooks/07_sales_forecasting.ipynb` |
| 8 | `notebooks/08_sql_business_analysis.ipynb` |
| 9 | `notebooks/09_powerbi_data_model.ipynb` |

Headless re-execution of all nine:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
```

## 7. Model generation

The pipeline stages above write every model artefact:

| Stage | Artefacts |
|---|---|
| `run_segmentation()` | `models/kmeans_customer_segmentation.pkl`, `rfm_scaler.pkl`, `pca_rfm.pkl` |
| `run_clv()` | `models/clv_model.pkl`, `clv_preprocessor.pkl` |
| `run_prediction()` | `models/revenue_prediction_model.pkl`, `revenue_prediction_preprocessor.pkl` |
| `run_forecasting()` | `models/forecasting_model.pkl` |

Each is accompanied by a `*_metadata.json` recording the selection rule, the
training window, the evaluation metrics and the library versions used.

## 8. SQL execution

`run_sql_workflow()` builds the database, validates it and runs every query.
To work with it directly:

```bash
python sql/load_database.py          # rebuild data/customer_revenue_intelligence.db
sqlite3 data/customer_revenue_intelligence.db < sql/analysis_queries.sql
sqlite3 data/customer_revenue_intelligence.db < sql/business_queries.sql
```

The reconciliation anchor — the query every surface must agree with:

```sql
SELECT COUNT(DISTINCT o.order_id)                           AS orders,
       COUNT(DISTINCT o.customer_id)                        AS customers,
       ROUND(SUM(oi.sales), 2)                              AS revenue,
       ROUND(SUM(oi.net_profit), 2)                         AS profit,
       ROUND(100.0 * SUM(oi.net_profit) / SUM(oi.sales), 2) AS margin_pct
FROM   order_items oi
JOIN   orders o ON o.order_id = oi.order_id
WHERE  oi.order_status = 'Delivered';
```

Expected: revenue ₹6.01 Cr, profit ₹1.40 Cr, margin 23.35%,
12,212 orders, 1,984 customers.

## 9. Streamlit execution

```bash
streamlit run app.py        # http://localhost:8501
```

If a page reports a missing artefact, the corresponding pipeline stage in
section 5 has not been run. Use the sidebar's cache-clear control after
regenerating data.

Headless tests:

```bash
python tests/test_streamlit_app.py
```

Expected: 40/40 checks pass.

## 10. Power BI usage

Power BI Desktop is a **Windows-only** application and was not available in
the build environment, so the `.pbix` is not in this repository.

Everything needed to build it is:

| Artefact | Location |
|---|---|
| Build guide (step by step) | `powerbi/POWERBI_BUILD_GUIDE.md` |
| Table extracts (CSV) | `powerbi/data/` |
| Power Query M scripts | `powerbi/powerquery/` |
| DAX measure library (84 measures) | `powerbi/dax/` |
| Theme JSON and background | `powerbi/theme/` |
| Relationship and table catalogues | `powerbi/relationships.csv`, `powerbi/table_catalog.csv` |
| Measure validation against SQL | `powerbi/validation/` |
| Page design mockups (not screenshots) | `outputs/figures/powerbi/mockups/` |

On a Windows machine: open Power BI Desktop, load the tables using the M
scripts, create the 9 relationships listed in
`relationships.csv`, mark `DimDate` as the date table, paste in the DAX
library, apply the theme, and build the nine pages from the build guide. Then
check the rendered figures against `powerbi/validation/`.

## 11. Rebuilding the documents

```bash
python scripts/report_facts.py          # refresh the fact pack from pipeline outputs
python scripts/report_diagrams.py       # report and deck diagrams
python scripts/build_report.py          # 40-page report (.docx + .pdf + checklist)
python scripts/build_presentation.py    # 22-slide deck (.pptx + .pdf)
python scripts/build_viva.py            # 18-file viva pack
python scripts/build_packaging.py       # README and this audit set
```

PDF conversion uses LibreOffice (`soffice`). Without it, the `.docx` and
`.pptx` are still produced and the script reports that the PDF step was
skipped.

## 12. Verifying the whole project

```bash
python scripts/audit_project.py         # full audit
python scripts/audit_project.py --quick # faster: skips the slowest re-runs
```

Expected: **135 checks, 134 pass,
0 fail.** The script exits non-zero if anything fails.

## 13. Expected runtime

On a typical laptop, the full pipeline (sections 4–5) takes a few minutes; the
notebooks take longer because they render every figure. The audit takes about
a minute in `--quick` mode.

## 14. If something does not reproduce

1. Check the Python and library versions first — the model metadata files
   record what each artefact was written with.
2. Confirm the seed is still 42 in `scripts/generate_dataset.py`.
3. Re-run `scripts/validate_dataset.py`; it compares the raw extract against
   the generator's own ground truth.
4. Run `python scripts/audit_project.py` — it names the failing check and the
   file involved.
