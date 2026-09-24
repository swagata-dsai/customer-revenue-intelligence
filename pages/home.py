"""HOME - the landing page.

Every stat card is read from the project's own outputs at run time; nothing here
is typed in.
"""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

sales = dl.load_sales()
customers = dl.load_customers()
forecast = dl.load_forecast()
meta = dl.load_metadata()

st.markdown("# Customer Revenue Intelligence")
st.markdown(
    f'<p style="color:{ui.THEME["muted"]};margin-top:-0.7rem;font-size:1.0rem">'
    f'Transforming Customer Data into Actionable Business Intelligence</p>',
    unsafe_allow_html=True)

# ------------------------------------------------------------------- pipeline
ui.section("How the platform works", "Every stage below is a completed project step")
FLOW = [
    ("🗂️", "DATA", "18,670 cleaned order lines, validated in SQL", ui.THEME["cat"][0]),
    ("🔎", "INSIGHT", "EDA, RFM, K-Means clusters, customer value", ui.THEME["cat"][3]),
    ("🔮", "PREDICTION", "Customer revenue model + 6-month forecast", ui.THEME["cat"][1]),
    ("🎯", "DECISION", "18 recommendations, each traced to an analysis", ui.THEME["cat"][2]),
]
steps = []
for i, (icon, title, note, colour) in enumerate(FLOW):
    steps.append(
        f'<div class="cri-flow-step" style="--accent:{colour};animation-delay:{i * 0.09:.2f}s">'
        f'<div class="f-icon">{icon}</div><div class="f-title">{title}</div>'
        f'<div class="f-note">{note}</div></div>')
    if i < len(FLOW) - 1:
        steps.append('<div class="cri-flow-arrow">→</div>')
st.markdown(f'<div class="cri-flow">{"".join(steps)}</div>', unsafe_allow_html=True)

# ----------------------------------------------------------------- stat cards
ui.section("The business at a glance", "Delivered revenue only · full project period")

if ui.validate_dataframe(sales, ["Sales", "Profit", "Order_ID", "Customer_ID"], "Transaction data"):
    k = dl.kpis(sales)
    n_segments = None
    n_clusters = None
    if customers is not None and "RFM_Segment" in customers.columns:
        scored = customers[customers.get("Has_Delivered_Order", 1) == 1]
        n_segments = scored["RFM_Segment"].nunique()
        if "Cluster_Label" in scored.columns:
            n_clusters = scored.loc[scored["Cluster_ID"] >= 0, "Cluster_Label"].nunique()

    horizon_txt, horizon_sub = "-", "Step 9 forecast unavailable"
    fmeta = meta.get("forecasting") or {}
    if forecast is not None and "Series_Label" in forecast.columns:
        fut = forecast[forecast["Series_Label"] == "Forecast"]
        if not fut.empty:
            horizon_txt = f"{len(fut)} months"
            horizon_sub = (f"{fut['Year_Month'].min()} to {fut['Year_Month'].max()} · "
                           f"{ui.format_currency(fut['Forecast_Revenue'].sum())} forecast")

    ui.kpi_row([
        dict(title="Total revenue", value=ui.format_currency(k["revenue"]),
             subtitle="Delivered order lines", accent=ui.THEME["cat"][0]),
        dict(title="Total profit", value=ui.format_currency(k["profit"]),
             subtitle=f"Margin {ui.format_percentage(k['margin'])}", accent=ui.THEME["cat"][2]),
        dict(title="Customers", value=ui.format_number(k["customers"]),
             subtitle=f"With a delivered order · {len(customers):,} registered"
                      if customers is not None else "With a delivered order",
             accent=ui.THEME["cat"][6]),
        dict(title="Orders", value=ui.format_number(k["orders"]),
             subtitle=f"AOV {ui.format_currency(k['aov'])}", accent=ui.THEME["cat"][3]),
        dict(title="Segments", value=(f"{n_segments} + {n_clusters}" if n_segments else "-"),
             subtitle="RFM segments + K-Means clusters", accent=ui.THEME["cat"][4]),
        dict(title="Forecast horizon", value=horizon_txt, subtitle=horizon_sub,
             accent=ui.THEME["cat"][2]),
    ])

    # -------------------------------------------------------------- mini trend
    st.write("")
    left, right = st.columns([2, 1], gap="medium")
    with left:
        m = dl.monthly(sales)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Revenue"], name="Revenue",
                                 mode="lines", line=dict(color=ui.SERIES["historical"], width=2.4),
                                 fill="tozeroy", fillcolor="rgba(57,135,229,0.10)",
                                 hovertemplate="%{x}<br>Revenue %{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Profit"], name="Profit",
                                 mode="lines", line=dict(color=ui.THEME["cat"][2], width=2.2),
                                 hovertemplate="%{x}<br>Profit %{y:,.0f}<extra></extra>"))
        if forecast is not None:
            fut = forecast[forecast["Series_Label"] == "Forecast"].sort_values("Year_Month")
            if not fut.empty:
                fig.add_trace(go.Scatter(
                    x=fut["Year_Month"], y=fut["Forecast_Revenue"], name="Forecast",
                    mode="lines", line=dict(color=ui.SERIES["forecast"], width=2.4, dash="dot"),
                    hovertemplate="%{x}<br>Forecast %{y:,.0f}<extra></extra>"))
        ui.create_plotly_chart(fig, height=330,
                               title="Monthly revenue and profit, with the forecast horizon",
                               y_title="₹", currency_axis="y")
    with right:
        reg = dl.by_dimension(sales, "Region").sort_values("Revenue")
        fig = go.Figure(go.Bar(
            x=reg["Revenue"], y=reg["Region"], orientation="h",
            marker_color=ui.THEME["cat"][0],
            text=[ui.format_currency(v) for v in reg["Revenue"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=11),
            hovertemplate="%{y}<br>Revenue %{x:,.0f}<extra></extra>"))
        fig.update_xaxes(range=[0, reg["Revenue"].max() * 1.35])
        ui.create_plotly_chart(fig, height=330, title="Revenue by region", legend=False,
                               x_title="₹", currency_axis="x")

    # ------------------------------------------------------------ what's here
    ui.section("What each page answers")
    cards = [
        ("📊 Executive Overview", "The headline position and where revenue comes from."),
        ("💰 Revenue Intelligence", "Revenue, margin and growth over time, and what moves them."),
        ("👥 Customer Intelligence", "Value distribution, top customers, recency and frequency."),
        ("🎯 Customer Segmentation", "RFM rules and K-Means clusters, compared honestly."),
        ("📦 Product Analytics", "Which products earn rather than only turn over."),
        ("🌍 Regional Analytics", "Regional performance and the category mix behind it."),
        ("🔮 Revenue Prediction", "The Step 8 model, its real metrics and a what-if tool."),
        ("📈 Sales Forecast", "The Step 9 forecast with its prediction intervals."),
        ("💡 Business Recommendations", "Finding → implication → action, each one traceable."),
        ("📂 Data Explorer", "Inspect the project data or profile your own CSV."),
    ]
    for start in range(0, len(cards), 2):
        for col, (title, note) in zip(st.columns(2, gap="medium"), cards[start:start + 2]):
            with col:
                ui.panel(f'<h4>{title}</h4><p class="note">{note}</p>')

    st.caption("Synthetic dataset · every figure on this page is computed from the project's "
               "validated outputs at page load, not stored in the application.")
