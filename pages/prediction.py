"""REVENUE PREDICTION - the Step 8 customer-level model, its real metrics, and a what-if tool."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Revenue Prediction",
               "The Step 8 machine-learning model: how much revenue a customer is likely to "
               "generate in the next quarter.", "🔮")

meta = (dl.load_metadata() or {}).get("revenue_prediction")
models = dl.load_models()
model_entry = models.get("revenue_prediction", {})
model = model_entry.get("object")
preds = dl.load_predictions()
quarters = dl.load_prediction_quarters()
comparison = dl.load_table("revenue_model_comparison")
importance = dl.load_table("revenue_feature_importance")

if meta is None:
    st.error("**`models/revenue_model_metadata.json` was not found.** This page reports the model "
             "exactly as Step 8 saved it, so it cannot show metrics without that file. Re-run "
             "`python src/prediction.py` to regenerate it.")
    st.stop()

# ------------------------------------------------------------- model identity
ui.section("Model information", "Read from the saved metadata - no metric is typed into this app")

test = meta.get("test_metrics", {})
val = meta.get("validation_metrics", {})
ui.kpi_row([
    dict(title="Model", value=str(meta.get("model_type", "-")),
         subtitle=f"Seed {meta.get('random_seed', '-')} · scikit-learn "
                  f"{meta.get('sklearn_version', '-')}", accent=ui.THEME["cat"][1]),
    dict(title="Test MAE", value=ui.format_currency(test.get("MAE"), unit="inr"),
         subtitle="Mean absolute error per customer-quarter", accent=ui.THEME["cat"][1]),
    dict(title="Test RMSE", value=ui.format_currency(test.get("RMSE"), unit="inr"),
         subtitle="Root mean squared error", accent=ui.THEME["cat"][1]),
    dict(title="Test R²", value=f"{test.get('R2', float('nan')):.3f}",
         subtitle="Share of variance explained - weak at customer level",
         accent=ui.THEME["warning"]),
    dict(title="Total bias", value=ui.format_percentage(test.get("Total_Bias_%"), signed=True,
                                                        already_pct=True),
         subtitle="Aggregate over/under-prediction on the test split",
         accent=ui.THEME["cat"][2]),
    dict(title="Rank correlation", value=f"{test.get('Spearman', float('nan')):.3f}",
         subtitle="Spearman - how well it orders customers", accent=ui.THEME["cat"][0]),
], per_row=6)

c1, c2 = st.columns([1.1, 1], gap="medium")
with c1:
    feats = meta.get("numeric_features", []) + meta.get("categorical_features", [])
    ui.panel(
        f'<h4>What the model predicts</h4>'
        f'<p><strong>Target.</strong> {meta.get("target", "-")}</p>'
        f'<p><strong>Prediction unit.</strong> {meta.get("prediction_unit", "-")}</p>'
        f'<p><strong>Training.</strong> {meta.get("training_period", "-")}</p>'
        f'<p><strong>Validation.</strong> {meta.get("validation_period", "-")} · '
        f'<strong>Test.</strong> {meta.get("test_period", "-")}</p>'
        f'<p><strong>Final fit.</strong> {meta.get("final_fit", "-")}</p>'
        f'<p><strong>Selection rule.</strong> {meta.get("selection_rule", "-")}</p>'
        f'<p class="note">{len(feats)} features: '
        f'{len(meta.get("numeric_features", []))} numeric, '
        f'{len(meta.get("categorical_features", []))} categorical.</p>')
with c2:
    ui.panel(
        f'<h4>How to use it honestly</h4>'
        f'<p>With an R² of <strong>{test.get("R2", float("nan")):.3f}</strong>, this model '
        f'explains only a small share of the variation in an individual customer&rsquo;s next '
        f'quarter. That is a real result on held-out data, not a failure to report.</p>'
        f'<p><strong>Valid uses:</strong> ranking customers for outreach (Spearman '
        f'{test.get("Spearman", float("nan")):.3f}), and aggregate planning - total bias on the '
        f'test split is {ui.format_percentage(test.get("Total_Bias_%"), signed=True, already_pct=True)}.</p>'
        f'<p><strong>Not valid:</strong> quoting one customer&rsquo;s predicted revenue as a '
        f'commitment.</p>'
        f'<p class="note">MAPE is deliberately not reported: many customer-quarters have an '
        f'actual of ₹0, which makes a percentage error undefined. WAPE '
        f'({test.get("WAPE_%", float("nan")):.1f}%) is shown instead in the model comparison.</p>')

# ------------------------------------------------------------ model comparison
if comparison is not None and "Model" in comparison.columns:
    ui.section("How the selected model compares", "Every candidate from Step 8, on the test split")
    comp = comparison.copy()
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=comp["Model"], y=comp["MAE"],
        marker_color=[ui.THEME["cat"][2] if s else (ui.THEME["muted"] if t == "Baseline"
                                                    else ui.THEME["cat"][0])
                      for s, t in zip(comp.get("Selected", False), comp.get("Type", ""))],
        text=[ui.format_currency(v, unit="inr") for v in comp["MAE"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=comp[["RMSE", "R2", "Type"]].values,
        hovertemplate=("%{x}<br>MAE ₹%{y:,.0f}<br>RMSE ₹%{customdata[0]:,.0f}"
                       "<br>R² %{customdata[1]:.4f}<br>%{customdata[2]}<extra></extra>")))
    fig.update_yaxes(range=[0, comp["MAE"].max() * 1.18])
    ui.create_plotly_chart(fig, height=380, legend=False, y_title="Test MAE ₹",
                           title="Test MAE by candidate model (green = selected, grey = baseline)")
    st.caption("The selected model is not the lowest-MAE model: Step 8 fixed the rule in advance - "
               "the simplest model family within 2% of the best validation RMSE - so the choice "
               "could not be made after seeing the test set.")
    with st.expander("Model comparison table"):
        st.dataframe(comp, use_container_width=True, hide_index=True)

# --------------------------------------------------------- actual vs predicted
if preds is not None and {"Actual_Revenue", "Predicted_Revenue"} <= set(preds.columns):
    ui.section("Predicted against actual", "Held-out test split only (2025 Q3-Q4)")
    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        sample = preds.sample(min(1500, len(preds)), random_state=42)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=sample["Actual_Revenue"], y=sample["Predicted_Revenue"], mode="markers",
            name="Customer-quarter",
            marker=dict(size=5, color=ui.SERIES["predicted"], opacity=0.55),
            customdata=sample[["Customer_ID", "Target_Period"]].values,
            hovertemplate=("%{customdata[0]} · %{customdata[1]}<br>Actual ₹%{x:,.0f}"
                           "<br>Predicted ₹%{y:,.0f}<extra></extra>")))
        lim = float(max(sample["Actual_Revenue"].max(), sample["Predicted_Revenue"].max()))
        fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines", name="Perfect prediction",
                                 line=dict(color=ui.THEME["muted"], width=1.4, dash="dash"),
                                 hoverinfo="skip"))
        ui.create_plotly_chart(fig, height=400, x_title="Actual revenue ₹",
                               y_title="Predicted revenue ₹",
                               title="Predicted vs actual, per customer-quarter")
        st.caption(f"A {len(sample):,}-row sample of the {len(preds):,} test rows, drawn with a "
                   f"fixed seed so the picture is reproducible. The spread around the diagonal "
                   f"is what an R² of {test.get('R2', float('nan')):.3f} looks like.")
    with c2:
        if quarters is not None and "Target_Period" in quarters.columns:
            q = quarters.copy()
            fig = go.Figure()
            fig.add_trace(go.Bar(x=q["Target_Period"], y=q["Actual_Revenue"], name="Actual",
                                 marker_color=ui.SERIES["historical"],
                                 hovertemplate="%{x}<br>Actual ₹%{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Bar(x=q["Target_Period"], y=q["Predicted_Revenue"], name="Predicted",
                                 marker_color=ui.SERIES["predicted"],
                                 hovertemplate="%{x}<br>Predicted ₹%{y:,.0f}<extra></extra>"))
            fig.update_layout(barmode="group")
            ui.create_plotly_chart(fig, height=400, y_title="₹", currency_axis="y",
                                   title="Quarterly totals: actual vs predicted")
            st.caption("Train quarters are an in-sample fit and match almost exactly by "
                       "construction; the out-of-sample quarters are the ones that matter.")

    err_dim = st.radio("Break the error down by",
                       [c for c in ["RFM_Segment_At_Cutoff", "Region", "Main_Category",
                                    "Target_Period"] if c in preds.columns],
                       horizontal=True, key="pred_err_dim",
                       format_func=lambda s: s.replace("_At_Cutoff", "").replace("_", " "))
    err = (preds.groupby(err_dim)
           .agg(MAE=("Absolute_Error", "mean"), Rows=("Customer_ID", "count"),
                Actual=("Actual_Revenue", "sum"), Predicted=("Predicted_Revenue", "sum"))
           .reset_index())
    err["Bias_%"] = 100 * (err["Predicted"] - err["Actual"]) / err["Actual"].replace(0, np.nan)
    err = err.sort_values("MAE")
    fig = go.Figure(go.Bar(
        x=err["MAE"], y=err[err_dim].astype(str), orientation="h",
        marker_color=ui.SERIES["predicted"],
        text=[ui.format_currency(v, unit="inr") for v in err["MAE"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=err[["Rows", "Bias_%"]].values,
        hovertemplate=("%{y}<br>MAE ₹%{x:,.0f}<br>%{customdata[0]:,} customer-quarters"
                       "<br>Bias %{customdata[1]:.1f}%<extra></extra>")))
    fig.update_xaxes(range=[0, err["MAE"].max() * 1.3])
    ui.create_plotly_chart(fig, height=max(300, 26 * len(err) + 120), legend=False,
                           x_title="Mean absolute error ₹", currency_axis="x",
                           title=f"Prediction error by {err_dim.replace('_At_Cutoff', '').replace('_', ' ').lower()}")
    st.caption("The error is largest where the revenue is largest - an absolute error of ₹11k on a "
               "Champion is a different thing from ₹3k on a dormant customer.")

if importance is not None and len(importance.columns) >= 2:
    with st.expander("Feature importance (Step 8 permutation importance)"):
        imp = importance.head(15).copy()
        cols = list(imp.columns)
        name_col, val_col = cols[0], cols[1]
        s = imp.sort_values(val_col)
        fig = go.Figure(go.Bar(x=s[val_col], y=s[name_col], orientation="h",
                               marker_color=ui.THEME["cat"][0],
                               hovertemplate="%{y}<br>%{x:,.4f}<extra></extra>"))
        ui.create_plotly_chart(fig, height=430, legend=False, x_title=val_col.replace("_", " "),
                               title="Permutation importance on the validation split")
        st.caption("Permutation importance measures how much the error grows when a feature is "
                   "shuffled. It is not a causal statement.")

# ------------------------------------------------------------- what-if tool
ui.section("What-if prediction tool", "Runs the saved Step 8 pipeline, not a re-implementation")

panel = dl.load_modeling_dataset()
if model_entry.get("status") != "loaded" or model is None:
    st.warning(f"**Interactive prediction is unavailable.** {model_entry.get('message', '')} "
               f"The metrics and charts above come from saved output files and are unaffected.")
elif panel is None:
    st.warning("**Interactive prediction is unavailable.** The Step 8 panel "
               "`data/processed/revenue_modeling_dataset.csv` was not found. The model needs a "
               "complete, real feature row as its starting point, and this app will not invent "
               "one.")
else:
    schema = list(getattr(model, "feature_names_in_", []))
    missing = [c for c in schema if c not in panel.columns]
    if not schema:
        st.warning("The saved pipeline does not expose a feature schema "
                   "(`feature_names_in_`), so the app cannot guarantee that the inputs match "
                   "what the model was trained on. The tool is disabled rather than risk a "
                   "misleading prediction.")
    elif missing:
        st.warning(f"The panel is missing {len(missing)} feature(s) the model needs "
                   f"({', '.join(missing[:5])}…), so the tool is disabled.")
    else:
        st.markdown(
            "The model was trained on 24 features, most of them 12-month aggregates and "
            "market-context ratios that a user cannot meaningfully invent. So this tool starts "
            "from **a real customer-quarter row** out of the Step 8 panel — every feature already "
            "has its computed value — and lets you move the handful of drivers that a business "
            "user can reason about. Everything else stays exactly as the pipeline computed it. "
            "No feature outside the trained schema can be entered.")

        test_rows = panel[panel["Split"] == "test"] if "Split" in panel.columns else panel
        c1, c2 = st.columns([1, 1], gap="medium")
        with c1:
            seg_col = "Main_Category"
            pick_region = st.selectbox("Region", sorted(test_rows["Region"].dropna().unique()),
                                       key="pred_region")
            subset = test_rows[test_rows["Region"] == pick_region]
            pick_cust = st.selectbox(f"Customer-quarter ({len(subset):,} available)",
                                     subset.apply(lambda r: f"{r['Customer_ID']} · "
                                                            f"{r['Target_Period']}", axis=1).tolist(),
                                     key="pred_customer")
        base_idx = subset.index[subset.apply(lambda r: f"{r['Customer_ID']} · "
                                                       f"{r['Target_Period']}", axis=1) == pick_cust][0]
        base = panel.loc[base_idx]

        with c2:
            ui.panel(
                f'<h4>{base["Customer_ID"]} · {base["Target_Period"]}</h4>'
                f'<p>Region {base["Region"]} · main category {base[seg_col]} · '
                f'{base.get("Acquisition_Status", "-")}</p>'
                f'<p class="note">Actual next-quarter revenue for this row: '
                f'<strong>{ui.format_currency(base.get("Next_Quarter_Revenue"), unit="inr")}</strong> '
                f'— known because this is a historical row from the held-out test split.</p>')

        st.markdown("**Adjust the drivers** (every other feature keeps its computed value):")
        adjustable = [
            ("Orders_12M", "Orders in the last 12 months", 0.0, 60.0, 1.0, "%.0f"),
            ("Rev_3M", "Revenue in the last 3 months (₹)", 0.0, None, 500.0, "%.0f"),
            ("AOV_12M", "Average order value, 12 months (₹)", 0.0, None, 250.0, "%.0f"),
            ("Recency_Days", "Days since last purchase", 0.0, 400.0, 1.0, "%.0f"),
            ("Avg_Discount_12M", "Average discount, 12 months", 0.0, 0.4, 0.01, "%.2f"),
            ("Categories_12M", "Distinct categories bought", 1.0, 6.0, 1.0, "%.0f"),
        ]
        adjustable = [a for a in adjustable if a[0] in schema]
        scenario = base.copy()
        cols = st.columns(3, gap="medium")
        for i, (field, label, lo, hi, step, fmt) in enumerate(adjustable):
            with cols[i % 3]:
                current = float(base[field])
                top = hi if hi is not None else float(max(panel[field].quantile(0.99),
                                                          current * 2, current + step))
                scenario[field] = st.slider(label, min_value=float(lo), max_value=float(top),
                                            value=float(min(max(current, lo), top)),
                                            step=float(step), format=fmt,
                                            key=f"pred_in_{field}")

        X_base = pd.DataFrame([base[schema].values], columns=schema)
        X_scen = pd.DataFrame([scenario[schema].values], columns=schema)
        for frame in (X_base, X_scen):
            for col in schema:
                if col in meta.get("numeric_features", []):
                    frame[col] = pd.to_numeric(frame[col], errors="coerce")

        try:
            p_base = float(model.predict(X_base)[0])
            p_scen = float(model.predict(X_scen)[0])
        except Exception as exc:                                  # noqa: BLE001
            st.error(f"The model could not score these inputs ({type(exc).__name__}). "
                     f"No prediction is shown rather than a guessed one.")
        else:
            delta = p_scen - p_base
            ui.kpi_row([
                dict(title="Predicted revenue (as recorded)",
                     value=ui.format_currency(p_base, unit="inr"),
                     subtitle="Model output on the unmodified feature row",
                     accent=ui.SERIES["predicted"]),
                dict(title="Predicted revenue (your scenario)",
                     value=ui.format_currency(p_scen, unit="inr"),
                     subtitle="Same model, your adjusted drivers",
                     accent=ui.SERIES["predicted"],
                     delta=f"{ui.format_currency(delta, unit='inr')} vs recorded",
                     delta_state="up" if delta > 0 else ("down" if delta < 0 else "flat")),
                dict(title="Actual (this historical row)",
                     value=ui.format_currency(base.get("Next_Quarter_Revenue"), unit="inr"),
                     subtitle="What really happened next quarter",
                     accent=ui.SERIES["historical"]),
                dict(title="Typical error at this level",
                     value=f"± {ui.format_currency(test.get('MAE'), unit='inr')}",
                     subtitle="Test MAE - the model's own accuracy",
                     accent=ui.THEME["warning"]),
            ], per_row=4)

            st.caption(
                f"Read the difference, not the level: the model's mean absolute error on held-out "
                f"data is {ui.format_currency(test.get('MAE'), unit='inr')} per customer-quarter, "
                f"which is larger than many of the predictions themselves. The tool is here to "
                f"show the direction and relative size of each driver's effect, which is what an "
                f"R² of {test.get('R2', float('nan')):.3f} with a Spearman of "
                f"{test.get('Spearman', float('nan')):.3f} supports.")

            changed = [(label, float(base[f]), float(scenario[f]))
                       for f, label, *_ in adjustable if float(base[f]) != float(scenario[f])]
            if changed:
                with st.expander("What you changed"):
                    st.dataframe(pd.DataFrame(changed, columns=["Driver", "Recorded value",
                                                                "Scenario value"]),
                                 use_container_width=True, hide_index=True)
