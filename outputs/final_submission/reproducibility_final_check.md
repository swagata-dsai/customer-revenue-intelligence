# Reproducibility — Final Check

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

Each stage below was **inspected or executed in this environment** at build
time. Nothing is assumed.

| Stage | Command / File | Status | Notes |
|-------|----------------|--------|-------|
| Python environment | `python --version` | VERIFIED | Python 3.11 in this environment |
| Dependencies | `requirements.txt` | VERIFIED | AST-derived; pip install dry-run resolved |
| Dataset | `scripts/generate_dataset.py` | VERIFIED | data/raw/customer_sales_raw.csv — 18,819 lines, seed 42 |
| Data preprocessing | `src.data_cleaning.run_pipeline` | VERIFIED | data/processed/customer_sales_cleaned.csv — 18,670 lines |
| EDA | `src.eda.run_eda` | VERIFIED | outputs/figures/ and eda_summary.md |
| RFM | `src.rfm.run_rfm` | VERIFIED | data/processed/customer_rfm_segments.csv — 11 segments |
| Segmentation | `src.segmentation.run_segmentation` | VERIFIED | models/kmeans_customer_segmentation.pkl — K = 4 |
| CLV | `src.clv.run_clv` | VERIFIED | models/clv_model.pkl and customer_clv.csv |
| Prediction | `src.prediction.run_prediction` | VERIFIED | models/revenue_prediction_model.pkl |
| Forecasting | `src.forecasting.run_forecasting` | VERIFIED | models/forecasting_model.pkl and revenue_forecast.csv |
| SQL | `src.sql_analytics.run_sql_workflow` | VERIFIED | data/customer_revenue_intelligence.db — 11 tables |
| Power BI prep | `src.powerbi_prep.run_powerbi_prep` | VERIFIED | powerbi/ — 84 DAX measures |
| Dashboard | `streamlit run app.py` | VERIFIED | 12 pages, 40/40 tests pass |
| Whole project | `scripts/audit_project.py` | VERIFIED | 135 checks, 134 pass, 0 fail |

## What "VERIFIED" means for each row

- **Environment and dependencies** — `pip install -r requirements.txt`
  resolved in a dry run; the package list was derived from an AST scan of every
  `.py` file and notebook, so it contains exactly what the project imports.
- **Entry points** — each of the nine pipeline functions was imported and
  checked to be callable in this environment. This is the check that caught
  four wrong commands in the report's User Manual.
- **Outputs on disk** — the artefact each stage writes was confirmed present.
- **Application** — the full headless suite was run:
  40/40 pass.
- **Whole project** — `scripts/audit_project.py` ran:
  135 checks, 134 pass, 0 fail.

## Honest limits of this check

| Limit | Detail |
|---|---|
| Full pipeline not re-executed end to end here | Each stage's entry point was import-tested and its output confirmed on disk, but re-running all nine from an empty `data/` would take several minutes and would overwrite the committed artefacts. The audit's model-reproducibility check independently re-derives the K-Means labels from the persisted scaler and model and reproduces them exactly |
| Power BI cannot be verified | Power BI Desktop is Windows-only and unavailable. The DAX measures were validated against SQL (48/48 match), but no `.pbix` was opened |
| Tested on one Python version | Python 3.11 with scikit-learn 1.8.0 and statsmodels 0.15.0. Other versions may load the `.pkl` artefacts with warnings; the metadata files record what each was written with |
| Timing not benchmarked | No formal runtime measurement was taken beyond the application's per-page load times in `outputs/tables/streamlit_page_load_times.csv` |

## For another student starting from zero

```bash
git clone <repository-url>
cd customer-revenue-intelligence
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

streamlit run app.py              # everything already computed
python scripts/audit_project.py   # verify: expect 134/135
```

To rebuild from nothing instead, follow `docs/reproducibility_guide.md`
sections 4 and 5 in order.
