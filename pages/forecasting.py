"""SALES FORECAST - the Step 9 time-series forecast, with its prediction intervals."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Sales Forecast",
               "Total company revenue for the months ahead, with the uncertainty the model "
               "itself reports.", "📈")

fc = dl.load_forecast()
meta = (dl.load_metadata() or {}).get("forecasting")
models = dl.load_models()
model_entry = models.get("forecasting", {})
comparison = dl.load_table("forecast_model_comparison")
backtest = dl.load_table("forecast_backtest_summary")

if not ui.validate_dataframe(fc, ["Year_Month", "Series_Label"], "Forecast output"):
    st.info("Re-run `python src/forecasting.py` (Step 9) to regenerate the forecast.")
    st.stop()
if meta is None:
    st.warning("`models/forecasting_metadata.json` was not found, so the model description and "
               "its accuracy figures cannot be shown. The chart below still uses the saved "
               "forecast output.")
    meta = {}

hist = fc[fc["Series_Label"] == "Historical"].sort_values("Year_Month")
back = fc[fc["Series_Label"] == "Forecast (backtest)"].sort_values("Year_Month")
fut = fc[fc["Series_Label"] == "Forecast"].sort_values("Year_Month")

metrics = meta.get("metrics", {})
test_m = metrics.get("test", {})

# ------------------------------------------------------------------ KPI cards
horizon = len(fut)
expected = float(fut["Forecast_Revenue"].sum()) if horizon else float("nan")
ui.kpi_row([
    dict(title="Forecast horizon", value=f"{horizon} months",
         subtitle=(f"{fut['Year_Month'].min()} to {fut['Year_Month'].max()}" if horizon else "-"),
         accent=ui.SERIES["forecast"]),
    dict(title="Expected revenue", value=ui.format_currency(expected),
         subtitle="Total across the horizon", accent=ui.SERIES["forecast"]),
    dict(title="Average forecast / month",
         value=ui.format_currency(expected / horizon if horizon else float("nan")),
         subtitle="Central forecast", accent=ui.SERIES["forecast"]),
    dict(title="Model used", value=str(meta.get("model_type", "-")).split(":")[0],
         subtitle=str(meta.get("model_type", "-")), accent=ui.THEME["cat"][3]),
    dict(title="Test MAPE", value=ui.format_percentage(test_m.get("MAPE_%"), decimals=2,
                                                       already_pct=True),
         subtitle="On 6 months the model never saw", accent=ui.THEME["cat"][3]),
    dict(title="Test MAE", value=ui.format_currency(test_m.get("MAE")),
         subtitle="Mean absolute error per month", accent=ui.THEME["cat"][3]),
], per_row=6)

if model_entry.get("status") != "loaded":
    st.info(f"The fitted forecasting object could not be loaded ({model_entry.get('message', '')}) "
            f"— this page reads the **saved forecast output**, which is what Step 9 produced, so "
            f"every number below is still the project's real result.")

# -------------------------------------------------------------------- chart
ui.section("Historical revenue and forecast",
           "Shaded band = prediction interval · it widens with the horizon, because month 6 is "
           "less certain than month 1")

show_backtest = st.toggle("Show the back-forecast on held-out months", value=True,
                          key="fc_backtest",
                          help="The validation and test forecasts, produced without the model "
                               "seeing those months. This is the evidence behind the accuracy "
                               "figures.")
band = st.radio("Prediction interval", ["95%", "80%", "None"], horizontal=True, key="fc_band")

fig = go.Figure()
if band != "None" and horizon:
    lo_col, hi_col = ("Lower_95", "Upper_95") if band == "95%" else ("Lower_80", "Upper_80")
    if lo_col in fut.columns and fut[lo_col].notna().any():
        fig.add_trace(go.Scatter(x=fut["Year_Month"], y=fut[hi_col], mode="lines",
                                 line=dict(width=0), showlegend=False, hoverinfo="skip",
                                 name=f"Upper {band}"))
        fig.add_trace(go.Scatter(
            x=fut["Year_Month"], y=fut[lo_col], mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(25,158,112,0.18)",
            name=f"{band} prediction interval",
            hovertemplate="%{x}<br>Lower ₹%{y:,.0f}<extra></extra>"))

fig.add_trace(go.Scatter(
    x=hist["Year_Month"], y=hist["Actual_Revenue"], mode="lines", name="Historical actual",
    line=dict(color=ui.SERIES["historical"], width=2.4),
    hovertemplate="%{x}<br>Actual ₹%{y:,.0f}<extra></extra>"))

if show_backtest and not back.empty:
    fig.add_trace(go.Scatter(
        x=back["Year_Month"], y=back["Forecast_Revenue"], mode="lines",
        name="Back-forecast (held-out months)",
        line=dict(color=ui.THEME["cat"][3], width=2, dash="dash"),
        hovertemplate="%{x}<br>Back-forecast ₹%{y:,.0f}<extra></extra>"))

if horizon:
    bridge = pd.concat([hist.tail(1)[["Year_Month"]].assign(
        Forecast_Revenue=hist.tail(1)["Actual_Revenue"].values), fut[["Year_Month",
                                                                      "Forecast_Revenue"]]])
    fig.add_trace(go.Scatter(
        x=bridge["Year_Month"], y=bridge["Forecast_Revenue"], mode="lines+markers",
        name="Forecast", line=dict(color=ui.SERIES["forecast"], width=2.8),
        marker=dict(size=6),
        hovertemplate="%{x}<br>Forecast ₹%{y:,.0f}<extra></extra>"))
    # A categorical x-axis cannot take add_vline's auto-annotation, so the line and
    # its label are added separately.
    cut = hist["Year_Month"].iloc[-1]
    fig.add_shape(type="line", x0=cut, x1=cut, y0=0, y1=1, yref="paper",
                  line=dict(color=ui.THEME["muted"], width=1, dash="dot"))
    fig.add_annotation(x=cut, y=1.02, yref="paper", text="forecast horizon starts",
                       showarrow=False, xanchor="right",
                       font=dict(color=ui.THEME["muted"], size=11))

ui.create_plotly_chart(fig, height=470, y_title="Monthly revenue ₹", currency_axis="y",
                       title="Monthly revenue: historical actual, back-forecast and forecast")

if not hist.empty and horizon:
    last_n = hist.tail(horizon)["Actual_Revenue"].sum()
    change = (expected - last_n) / last_n if last_n else float("nan")
    st.caption(
        f"The forecast of {ui.format_currency(expected)} for the next {horizon} months compares "
        f"with {ui.format_currency(last_n)} actually delivered in the previous {horizon} months "
        f"({ui.format_percentage(change, signed=True)}). The {band if band != 'None' else '95%'} "
        f"interval is the model's own statement of uncertainty - plan to the line, stress-test to "
        f"the lower edge.")

# -------------------------------------------------------------- forecast table
ui.section("Forecast table", "The saved Step 9 output, unmodified")
if horizon:
    tbl = fut[["Year_Month", "Forecast_Revenue", "Lower_80", "Upper_80", "Lower_95",
               "Upper_95"]].copy()
    tbl.columns = ["Period", "Forecast Revenue", "Lower 80%", "Upper 80%", "Lower 95%",
                   "Upper 95%"]
    st.dataframe(tbl, use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(format="₹%.0f")
                                for c in tbl.columns if c != "Period"})
    total_row = pd.DataFrame([{
        "Period": "TOTAL", "Forecast Revenue": tbl["Forecast Revenue"].sum(),
        "Lower 80%": tbl["Lower 80%"].sum(), "Upper 80%": tbl["Upper 80%"].sum(),
        "Lower 95%": tbl["Lower 95%"].sum(), "Upper 95%": tbl["Upper 95%"].sum()}])
    st.caption(f"Horizon total: **{ui.format_currency(total_row['Forecast Revenue'].iloc[0])}** "
               f"(80% interval {ui.format_currency(total_row['Lower 80%'].iloc[0])} to "
               f"{ui.format_currency(total_row['Upper 80%'].iloc[0])}). Summing interval bounds "
               f"is an approximation - the monthly bounds are not independent.")
    ui.download_button(pd.concat([tbl, total_row]), "revenue_forecast.csv", key="fc_dl")
else:
    st.warning("The saved output contains no future forecast rows.")

# ------------------------------------------------------------------- accuracy
ui.section("How accurate has it been?", "Every figure read from the Step 9 metadata and tables")

c1, c2 = st.columns([1, 1.1], gap="medium")
with c1:
    rows = []
    for split_name, key in [("Validation", "validation"), ("Test", "test")]:
        m = metrics.get(key, {})
        if m:
            rows.append({"Split": split_name, "MAE": m.get("MAE"), "RMSE": m.get("RMSE"),
                         "MAPE %": m.get("MAPE_%"), "sMAPE %": m.get("sMAPE_%"),
                         "WAPE %": m.get("WAPE_%")})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                     column_config={"MAE": st.column_config.NumberColumn(format="₹%.0f"),
                                    "RMSE": st.column_config.NumberColumn(format="₹%.0f")})
    if "backtest_mean_MAPE_%" in metrics:
        st.caption(f"Mean rolling-backtest MAPE: **{metrics['backtest_mean_MAPE_%']:.2f}%** - "
                   f"this was the metric the model was selected on, fixed before the test set "
                   f"was touched.")
    ui.panel(
        f'<h4>Model and selection</h4>'
        f'<p><strong>Model.</strong> {meta.get("model_type", "-")}</p>'
        f'<p><strong>Fitted on.</strong> {meta.get("training_period_final_fit", "-")}</p>'
        f'<p><strong>Split.</strong> train {meta.get("evaluation_split", {}).get("train", "-")} · '
        f'validation {meta.get("evaluation_split", {}).get("validation", "-")} · '
        f'test {meta.get("evaluation_split", {}).get("test", "-")}</p>'
        f'<p><strong>Selection rule.</strong> {meta.get("selection_rule", "-")}</p>'
        f'<p class="note">{meta.get("intervals", "-")}</p>')
with c2:
    if comparison is not None and "Model" in comparison.columns:
        comp = comparison.copy()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=comp["Model"].str.split(":").str[0], y=comp["Test_MAPE_%"],
            marker_color=[ui.SERIES["forecast"]
                          if str(meta.get("model_type", "")).startswith(str(m).split(":")[0])
                          else (ui.THEME["muted"] if f == "Naive" else ui.THEME["cat"][0])
                          for m, f in zip(comp["Model"], comp["Family"])],
            text=[f"{v:.2f}%" for v in comp["Test_MAPE_%"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=10),
            customdata=comp[["Test_MAE", "Val_MAPE_%"]].values,
            hovertemplate=("%{x}<br>Test MAPE %{y:.2f}%<br>Test MAE ₹%{customdata[0]:,.0f}"
                           "<br>Validation MAPE %{customdata[1]:.2f}%<extra></extra>")))
        fig.update_yaxes(range=[0, comp["Test_MAPE_%"].max() * 1.2])
        ui.create_plotly_chart(fig, height=340, legend=False, y_title="Test MAPE %",
                               title="Candidate models on the test months "
                                     "(green = selected, grey = naive baseline)")
        with st.expander("Full model comparison"):
            st.dataframe(comp, use_container_width=True, hide_index=True)

if backtest is not None:
    with st.expander("Rolling backtest detail"):
        st.dataframe(backtest, use_container_width=True, hide_index=True)
        st.caption("Each fold re-fits the model on data up to a cut-off and forecasts forward, "
                   "so the accuracy reflects repeated honest forecasts rather than one lucky "
                   "window.")

with st.expander("What this forecast does and does not include"):
    st.markdown(f"""
- **Company level, univariate.** It forecasts total monthly delivered revenue from its own
  history. There is no regional or category breakdown, and no promotional, pricing or external
  driver enters the model.
- **Fitted on {meta.get('training_period_final_fit', '36 months')}**, which is a short series.
  Step 9 tested for seasonality and did not find a significant seasonal signal at that length,
  so the model does not impose one.
- **The intervals are the model's**, not a rule of thumb. They widen with the horizon.
- **It ages.** Re-run Step 9 as new months land; the page will pick up the new saved output
  automatically.
""")
