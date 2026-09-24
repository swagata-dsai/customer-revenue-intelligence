"""DATA EXPLORER - inspect the project's data, or profile a CSV of your own."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Data Explorer",
               "Browse the project's own tables, or upload a CSV and have it profiled. Nothing "
               "you upload is written into the project's data.", "📂")

REQUIRED_PROJECT_COLUMNS = ["Order_ID", "Order_Date", "Customer_ID", "Product_ID", "Quantity",
                            "Sales", "Profit", "Order_Status"]

tab_project, tab_upload = st.tabs(["Project data", "Upload a CSV"])


# ---------------------------------------------------------------- profiling
def quality_scorecard(df: pd.DataFrame, required: list[str] | None = None,
                      date_cols: list[str] | None = None) -> pd.DataFrame:
    """Data-quality checks, each one an actual calculation with its own number.

    There is no single invented "quality %": each row states what was measured, the
    count, and the share of cells or rows it affects.
    """
    rows = []
    n_rows, n_cols = df.shape
    cells = max(n_rows * n_cols, 1)

    missing = int(df.isna().sum().sum())
    rows.append({"Check": "Missing values",
                 "Measure": f"{missing:,} empty cells",
                 "Share": f"{100 * missing / cells:.2f}% of all cells",
                 "Status": "Clean" if missing == 0 else "Review"})

    cols_with_missing = int((df.isna().sum() > 0).sum())
    rows.append({"Check": "Columns containing missing values",
                 "Measure": f"{cols_with_missing} of {n_cols} columns",
                 "Share": f"{100 * cols_with_missing / max(n_cols, 1):.1f}% of columns",
                 "Status": "Clean" if cols_with_missing == 0 else "Review"})

    dupes = int(df.duplicated().sum())
    rows.append({"Check": "Fully duplicated rows",
                 "Measure": f"{dupes:,} rows",
                 "Share": f"{100 * dupes / max(n_rows, 1):.2f}% of rows",
                 "Status": "Clean" if dupes == 0 else "Review"})

    # invalid dates: columns that look like dates but will not parse
    date_candidates = date_cols or [c for c in df.columns
                                    if "date" in str(c).lower() or "time" in str(c).lower()]
    for col in date_candidates:
        parsed = pd.to_datetime(df[col], errors="coerce")
        bad = int(parsed.isna().sum() - df[col].isna().sum())
        rows.append({"Check": f"Unparseable values in '{col}'",
                     "Measure": f"{max(bad, 0):,} values",
                     "Share": f"{100 * max(bad, 0) / max(n_rows, 1):.2f}% of rows",
                     "Status": "Clean" if bad <= 0 else "Review"})

    numeric = df.select_dtypes(include="number")
    if not numeric.empty:
        inf_count = int(np.isinf(numeric.to_numpy(dtype="float64", na_value=np.nan)).sum())
        rows.append({"Check": "Infinite numeric values",
                     "Measure": f"{inf_count:,} values",
                     "Share": f"{100 * inf_count / max(numeric.size, 1):.3f}% of numeric cells",
                     "Status": "Clean" if inf_count == 0 else "Review"})
        # IQR outliers, reported as a count - not as a judgement that they are errors
        outliers = 0
        for col in numeric.columns:
            s = numeric[col].dropna()
            if len(s) < 8:
                continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                outliers += int(((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum())
        rows.append({"Check": "Values beyond 1.5 x IQR (any numeric column)",
                     "Measure": f"{outliers:,} values",
                     "Share": f"{100 * outliers / max(numeric.size, 1):.2f}% of numeric cells",
                     "Status": "Informational"})
        negatives = int((numeric < 0).sum().sum())
        rows.append({"Check": "Negative numeric values",
                     "Measure": f"{negatives:,} values",
                     "Share": f"{100 * negatives / max(numeric.size, 1):.2f}% of numeric cells",
                     "Status": "Informational"})

    if required:
        present = [c for c in required if c in df.columns]
        rows.append({"Check": "Required columns present",
                     "Measure": f"{len(present)} of {len(required)}",
                     "Share": ", ".join(c for c in required if c not in df.columns) or "all present",
                     "Status": "Clean" if len(present) == len(required) else "Review"})
    return pd.DataFrame(rows)


def profile(df: pd.DataFrame, name: str, required: list[str] | None = None) -> None:
    c1, c2, c3, c4 = st.columns(4, gap="small")
    with c1:
        ui.create_kpi_card("Rows", f"{len(df):,}", name, ui.THEME["cat"][0])
    with c2:
        ui.create_kpi_card("Columns", f"{df.shape[1]:,}", "Fields in the file",
                           ui.THEME["cat"][6])
    with c3:
        ui.create_kpi_card("Missing cells", f"{int(df.isna().sum().sum()):,}",
                           f"{100 * df.isna().sum().sum() / max(df.size, 1):.2f}% of cells",
                           ui.THEME["cat"][3])
    with c4:
        ui.create_kpi_card("Duplicate rows", f"{int(df.duplicated().sum()):,}",
                           "Identical across every column", ui.THEME["cat"][1])

    st.write("")
    ui.section("Preview", "First 100 rows")
    st.dataframe(df.head(100), use_container_width=True, height=320)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        ui.section("Columns and types")
        info = pd.DataFrame({
            "Column": df.columns,
            "Type": [str(t) for t in df.dtypes],
            "Non-null": df.notna().sum().values,
            "Missing": df.isna().sum().values,
            "Missing %": (100 * df.isna().mean()).round(2).values,
            "Unique": [int(df[c].nunique(dropna=True)) for c in df.columns],
        })
        st.dataframe(info, use_container_width=True, hide_index=True, height=320)
    with c2:
        ui.section("Numerical summary")
        num = df.select_dtypes(include="number")
        if num.empty:
            st.info("This file has no numeric columns to summarise.")
        else:
            st.dataframe(num.describe().T.round(3), use_container_width=True, height=320)

    ui.section("Data quality scorecard",
               "Each row is an actual count - there is no single invented quality score")
    card = quality_scorecard(df, required=required)
    st.dataframe(card, use_container_width=True, hide_index=True)
    st.caption("**Method.** Missing values count empty cells; duplicates count rows identical in "
               "every column; date checks count values that fail to parse; the IQR row counts "
               "values outside 1.5 x IQR of their own column and is informational - in this "
               "project's data such values were investigated in Step 3 and found to be genuine "
               "high-value orders, not errors.")

    miss = df.isna().mean().sort_values(ascending=False)
    miss = miss[miss > 0].head(15)
    if not miss.empty:
        fig = go.Figure(go.Bar(x=(100 * miss.values), y=list(miss.index), orientation="h",
                               marker_color=ui.THEME["warning"],
                               hovertemplate="%{y}<br>%{x:.2f}% missing<extra></extra>"))
        ui.create_plotly_chart(fig, height=max(240, 26 * len(miss) + 100), legend=False,
                               x_title="% missing", title="Columns with missing values")


# -------------------------------------------------------------- project data
with tab_project:
    sources = {
        "Cleaned transactions (fact table)": ("sales", REQUIRED_PROJECT_COLUMNS),
        "Customer dimension (RFM, cluster, customer value)": ("customers", ["Customer_ID"]),
        "Monthly forecast series (Step 9)": ("forecast", ["Year_Month"]),
        "Revenue predictions, test split (Step 8)": ("predictions", ["Customer_ID"]),
    }
    choice = st.selectbox("Dataset", list(sources), key="de_source")
    kind, required = sources[choice]
    loader = {"sales": dl.load_sales, "customers": dl.load_customers,
              "forecast": dl.load_forecast, "predictions": dl.load_predictions}[kind]
    df = loader()

    if not ui.validate_dataframe(df, None, choice):
        st.stop()

    work = df
    if kind == "sales":
        work = ui.sales_filters(df, key="de", fields=("date", "region", "category", "segment"))
        if work.empty:
            st.warning("No rows match the current filters.")
            st.stop()

    profile(work, choice, required)

    ui.section("Download", "The rows currently shown, as a CSV")
    st.caption("This writes a new file to your computer. The project's official processed "
               "dataset in `data/processed/` is never modified by this app.")
    ui.download_button(work, f"{kind}_export.csv", label="Download this view as CSV",
                       key="de_project_dl")


# ---------------------------------------------------------------- user upload
with tab_upload:
    st.markdown("Upload any CSV to have it profiled with the same checks. The file is held in "
                "memory for this session only - it is **not** saved into the project and does "
                "not affect any other page.")
    up = st.file_uploader("CSV file", type=["csv"], key="de_upload")

    if up is None:
        st.info("No file uploaded yet. Drop a CSV above to profile it.")
    else:
        raw = up.getvalue()
        size_mb = len(raw) / 1e6
        user_df = None
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                user_df = pd.read_csv(io.BytesIO(raw), encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.EmptyDataError:
                st.error(f"**{up.name} is empty.** There are no rows to read.")
                break
            except pd.errors.ParserError as exc:
                st.error(f"**{up.name} could not be parsed as CSV.** "
                         f"The reader stopped at: {str(exc)[:200]}")
                break
        if user_df is None:
            st.stop()
        if user_df.empty:
            st.error(f"**{up.name} parsed, but contains no rows.**")
            st.stop()

        ui.panel(f'<h4>{up.name}</h4><p class="note">{size_mb:.2f} MB · {len(user_df):,} rows · '
                 f'{user_df.shape[1]} columns</p>')

        profile(user_df, up.name)

        ui.section("Filter and download", "Optional - narrow the file before exporting it")
        filtered = user_df
        cat_cols = [c for c in user_df.columns
                    if user_df[c].dtype == object and 1 < user_df[c].nunique() <= 50]
        num_cols = list(user_df.select_dtypes(include="number").columns)
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            if cat_cols:
                col = st.selectbox("Filter on a text column", ["(none)"] + cat_cols,
                                   key="de_up_catcol")
                if col != "(none)":
                    vals = st.multiselect("Keep these values",
                                          sorted(user_df[col].dropna().unique().tolist()),
                                          key="de_up_catvals", placeholder="All")
                    if vals:
                        filtered = filtered[filtered[col].isin(vals)]
            else:
                st.caption("No text column with a manageable number of distinct values.")
        with c2:
            if num_cols:
                col = st.selectbox("Filter on a numeric column", ["(none)"] + num_cols,
                                   key="de_up_numcol")
                if col != "(none)":
                    series = pd.to_numeric(user_df[col], errors="coerce")
                    lo, hi = float(series.min()), float(series.max())
                    if np.isfinite(lo) and np.isfinite(hi) and lo < hi:
                        rng = st.slider(f"Range of {col}", lo, hi, (lo, hi), key="de_up_numrange")
                        filtered = filtered[series.between(*rng).fillna(False).values]
                    else:
                        st.caption("This column has no usable range to filter on.")
            else:
                st.caption("No numeric columns to filter on.")

        st.caption(f"{len(filtered):,} of {len(user_df):,} rows selected.")
        ui.download_button(filtered, f"processed_{up.name}",
                           label="Download processed data", key="de_up_dl")
        st.caption("The download contains exactly the rows shown above. Your upload is never "
                   "written into `data/processed/`, so the project's official dataset stays "
                   "untouched.")
