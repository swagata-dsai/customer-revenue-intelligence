"""EXECUTIVE OVERVIEW - the whole business on one screen."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Executive Overview",
               "Headline performance and where revenue comes from. Delivered order lines only.",
               "📊")

sales = dl.load_sales()
if not ui.validate_dataframe(sales, ["Sales", "Profit", "Order_ID", "Customer_ID", "Region",
                                     "Category"], "Transaction data"):
    st.stop()

flt = ui.sales_filters(sales, key="exec", fields=("date", "region", "category", "segment"))
ui.active_filter_note(flt, sales)
if flt.empty:
    st.warning("No order lines match the current filters. Widen them to see the overview.")
    st.stop()

k = dl.kpis(flt)

# ------------------------------------------------------------------ KPI cards
ui.kpi_row([
    dict(title="Total revenue", value=ui.format_currency(k["revenue"]),
         subtitle=f"{k['order_lines']:,} delivered lines", accent=ui.THEME["cat"][0]),
    dict(title="Total profit", value=ui.format_currency(k["profit"]),
         subtitle=f"Cost {ui.format_currency(k['cost'])}", accent=ui.THEME["cat"][2]),
    dict(title="Profit margin", value=ui.format_percentage(k["margin"]),
         subtitle="Profit / revenue", accent=ui.THEME["cat"][2]),
    dict(title="Total customers", value=ui.format_number(k["customers"]),
         subtitle=f"{k['orders_per_customer']:.2f} orders each", accent=ui.THEME["cat"][6]),
    dict(title="Total orders", value=ui.format_number(k["orders"]),
         subtitle=f"{k['qty_per_order']:.2f} units per order", accent=ui.THEME["cat"][3]),
    dict(title="Average order value", value=ui.format_currency(k["aov"], unit="inr"),
         subtitle=f"Profit per order {ui.format_currency(k['profit_per_order'], unit='inr')}",
         accent=ui.THEME["cat"][3]),
])

# --------------------------------------------------------------------- trends
ui.section("Revenue and profit over time",
           "Both series are rupees, so they share one axis - this report never uses a second y-axis")

m = dl.monthly(flt)
if ui.validate_dataframe(m, ["Year_Month", "Revenue", "Profit"], "Monthly aggregation"):
    tab_combined, tab_revenue, tab_profit = st.tabs(
        ["Revenue and profit", "Revenue trend", "Profit trend"])

    with tab_combined:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Revenue"], name="Revenue", mode="lines",
                                 line=dict(color=ui.SERIES["historical"], width=2.4),
                                 fill="tozeroy", fillcolor="rgba(57,135,229,0.10)",
                                 hovertemplate="%{x}<br>Revenue ₹%{y:,.0f}<extra></extra>"))
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Profit"], name="Profit", mode="lines",
                                 line=dict(color=ui.THEME["cat"][2], width=2.2),
                                 hovertemplate="%{x}<br>Profit ₹%{y:,.0f}<extra></extra>"))
        ui.create_plotly_chart(fig, height=380, y_title="₹", currency_axis="y",
                               title="Monthly revenue and profit")
        peak = m.loc[m["Revenue"].idxmax()]
        st.caption(f"Highest month in the current selection: **{peak['Year_Month']}** at "
                   f"{ui.format_currency(peak['Revenue'])}.")

    with tab_revenue:
        fig = go.Figure(go.Scatter(
            x=m["Year_Month"], y=m["Revenue"], mode="lines+markers", name="Revenue",
            line=dict(color=ui.SERIES["historical"], width=2.4), marker=dict(size=5),
            hovertemplate="%{x}<br>Revenue ₹%{y:,.0f}<extra></extra>"))
        ui.create_plotly_chart(fig, height=360, y_title="₹", currency_axis="y", legend=False,
                               title="Monthly revenue trend")

    with tab_profit:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Profit"], mode="lines+markers",
                                 name="Profit", line=dict(color=ui.THEME["cat"][2], width=2.4),
                                 marker=dict(size=5),
                                 hovertemplate="%{x}<br>Profit ₹%{y:,.0f}<extra></extra>"))
        ui.create_plotly_chart(fig, height=360, y_title="₹", currency_axis="y", legend=False,
                               title="Monthly profit trend")

# ------------------------------------------------------------------ breakdown
ui.section("Where the revenue comes from")

left, right = st.columns(2, gap="medium")

with left:
    cat = dl.by_dimension(flt, "Category").sort_values("Revenue")
    if not cat.empty:
        fig = go.Figure(go.Bar(
            x=cat["Revenue"], y=cat["Category"], orientation="h",
            marker_color=ui.THEME["cat"][3],
            customdata=cat[["Margin_%", "Revenue_Share_%", "Quantity"]].values,
            text=[f"{ui.format_currency(v)} · {mg:.1f}% margin"
                  for v, mg in zip(cat["Revenue"], cat["Margin_%"])],
            textposition="outside", textfont=dict(color=ui.THEME["ink"], size=11),
            hovertemplate=("%{y}<br>Revenue ₹%{x:,.0f}<br>Margin %{customdata[0]:.1f}%"
                           "<br>Share %{customdata[1]:.1f}%<br>Units %{customdata[2]:,.0f}"
                           "<extra></extra>")))
        fig.update_xaxes(range=[0, cat["Revenue"].max() * 1.55])
        ui.create_plotly_chart(fig, height=340, legend=False, x_title="₹", currency_axis="x",
                               title="Revenue by category, with each category's margin")

with right:
    reg = dl.by_dimension(flt, "Region").sort_values("Revenue")
    if not reg.empty:
        fig = go.Figure(go.Bar(
            x=reg["Revenue"], y=reg["Region"], orientation="h",
            marker_color=ui.THEME["cat"][0],
            customdata=reg[["Margin_%", "Customers", "AOV"]].values,
            text=[f"{ui.format_currency(v)} · {s:.1f}%"
                  for v, s in zip(reg["Revenue"], reg["Revenue_Share_%"])],
            textposition="outside", textfont=dict(color=ui.THEME["ink"], size=11),
            hovertemplate=("%{y}<br>Revenue ₹%{x:,.0f}<br>Margin %{customdata[0]:.1f}%"
                           "<br>Customers %{customdata[1]:,.0f}<br>AOV ₹%{customdata[2]:,.0f}"
                           "<extra></extra>")))
        fig.update_xaxes(range=[0, reg["Revenue"].max() * 1.45])
        ui.create_plotly_chart(fig, height=340, legend=False, x_title="₹", currency_axis="x",
                               title="Revenue by region, with share of the selection")

# ------------------------------------------------------ segment contribution
ui.section("Customer segment contribution",
           "Share of revenue against share of customers - the gap is the point")

seg = dl.by_dimension(flt, "RFM_Segment")
if not seg.empty:
    seg = seg[seg["RFM_Segment"] != "No delivered order"].copy()
    total_customers = seg["Customers"].sum()
    seg["Customer_Share_%"] = 100 * seg["Customers"] / total_customers if total_customers else 0
    seg = seg.sort_values("Revenue_Share_%").tail(8)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=seg["RFM_Segment"], x=seg["Revenue_Share_%"], name="% of revenue",
                         orientation="h", marker_color=ui.THEME["cat"][0],
                         text=[f"{v:.1f}%" for v in seg["Revenue_Share_%"]],
                         textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{y}<br>%{x:.1f}% of revenue<extra></extra>"))
    fig.add_trace(go.Bar(y=seg["RFM_Segment"], x=seg["Customer_Share_%"], name="% of customers",
                         orientation="h", marker_color=ui.THEME["cat"][4],
                         text=[f"{v:.1f}%" for v in seg["Customer_Share_%"]],
                         textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{y}<br>%{x:.1f}% of customers<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(range=[0, max(seg["Revenue_Share_%"].max(),
                                   seg["Customer_Share_%"].max()) * 1.25])
    ui.create_plotly_chart(fig, height=400, x_title="% of the current selection",
                           title="Revenue share vs customer share, by RFM segment")

    top = seg.loc[seg["Revenue_Share_%"].idxmax()]
    st.caption(f"**{top['RFM_Segment']}** is {top['Customer_Share_%']:.1f}% of the customers in "
               f"this selection and {top['Revenue_Share_%']:.1f}% of its revenue. Segment "
               f"assignments are the Step 5 snapshot at {dl.REFERENCE_DATE}; the revenue beside "
               f"them responds to the filters.")

with st.expander("Definitions used on this page"):
    st.markdown(f"""
- **Revenue** - value of **Delivered** order lines. Returned and Cancelled lines are excluded,
  which is the project's revenue rule from Step 3 onwards. In the current selection
  {ui.format_percentage(k['not_realised'])} of booked value was not realised
  ({ui.format_currency(k['booked'] - k['revenue'])} of {ui.format_currency(k['booked'])}).
- **Orders** - orders with at least one delivered line.
- **Customers** - distinct customers with a delivered order in the selection.
- **AOV** - revenue ÷ orders.
- **RFM segment** - the Step 5 rule-based segment, assigned once at the
  {dl.REFERENCE_DATE} reference date. It does not move with the date filter.
""")
