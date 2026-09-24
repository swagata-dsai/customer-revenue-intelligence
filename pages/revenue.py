"""REVENUE INTELLIGENCE - revenue, margin, growth and what moves them."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Revenue Intelligence",
               "How revenue and margin move over time, and which categories, regions and "
               "discount levels drive them.", "💰")

sales = dl.load_sales()
if not ui.validate_dataframe(sales, ["Sales", "Profit", "Category", "Region", "Discount"],
                             "Transaction data"):
    st.stop()

flt = ui.sales_filters(sales, key="rev",
                       fields=("date", "region", "category", "sub_category"))
ui.active_filter_note(flt, sales)
if flt.empty:
    st.warning("No order lines match the current filters.")
    st.stop()

k = dl.kpis(flt)
m = dl.monthly(flt)

# ------------------------------------------------------------- growth figures
# Year-over-year growth is computed on the filtered slice, on complete years only,
# so a part-year at the edge of a date filter cannot masquerade as a collapse.
d = dl.delivered(flt)
by_year = d.groupby("Year")["Sales"].sum().sort_index()
months_per_year = d.groupby("Year")["Year_Month"].nunique()
full_years = months_per_year[months_per_year == 12].index
growth_txt, growth_sub, growth_state = "-", "Needs two complete years in the selection", "flat"
if len(full_years) >= 2:
    y2, y1 = full_years[-1], full_years[-2]
    g = (by_year[y2] - by_year[y1]) / by_year[y1]
    growth_txt = ui.format_percentage(g, signed=True)
    growth_sub = f"{y1} → {y2}, complete years only"
    growth_state = "up" if g > 0 else ("down" if g < 0 else "flat")

ui.kpi_row([
    dict(title="Total revenue", value=ui.format_currency(k["revenue"]),
         subtitle=f"Over {k['months']} months", accent=ui.THEME["cat"][0]),
    dict(title="Revenue growth", value=growth_txt, subtitle=growth_sub,
         accent=ui.THEME["cat"][0], delta_state=growth_state),
    dict(title="Average monthly revenue", value=ui.format_currency(k["avg_monthly_revenue"]),
         subtitle="Months with delivered revenue only", accent=ui.THEME["cat"][6]),
    dict(title="Total profit", value=ui.format_currency(k["profit"]),
         subtitle=f"Per order {ui.format_currency(k['profit_per_order'], unit='inr')}",
         accent=ui.THEME["cat"][2]),
    dict(title="Profit margin", value=ui.format_percentage(k["margin"]),
         subtitle="Profit / revenue", accent=ui.THEME["cat"][2]),
], per_row=5)

# --------------------------------------------------------------------- trends
ui.section("Trends", "Rupee series and ratio series are kept on separate charts")

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Revenue"], name="Revenue", mode="lines",
                             line=dict(color=ui.SERIES["historical"], width=2.4),
                             hovertemplate="%{x}<br>Revenue ₹%{y:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=m["Year_Month"], y=m["Profit"], name="Profit", mode="lines",
                             line=dict(color=ui.THEME["cat"][2], width=2.2),
                             fill="tozeroy", fillcolor="rgba(25,158,112,0.10)",
                             hovertemplate="%{x}<br>Profit ₹%{y:,.0f}<extra></extra>"))
    ui.create_plotly_chart(fig, height=350, y_title="₹", currency_axis="y",
                           title="Monthly revenue and profit")
with c2:
    fig = go.Figure(go.Scatter(
        x=m["Year_Month"], y=m["Margin_%"], mode="lines", name="Profit margin %",
        line=dict(color=ui.THEME["cat"][3], width=2.4),
        hovertemplate="%{x}<br>Margin %{y:.2f}%<extra></extra>"))
    overall = 100 * k["margin"]
    fig.add_hline(y=overall, line_dash="dash", line_color=ui.THEME["muted"],
                  annotation_text=f"selection average {overall:.1f}%",
                  annotation_font_color=ui.THEME["muted"], annotation_font_size=11)
    ui.create_plotly_chart(fig, height=350, y_title="%", legend=False,
                           title="Monthly profit margin")

# growth bars
yr = (d.groupby("Year").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum")).reset_index())
yr["Complete"] = yr["Year"].isin(full_years)
yr["Revenue_Growth_%"] = yr["Revenue"].pct_change() * 100
if len(yr) > 1:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        fig = go.Figure(go.Bar(
            x=yr["Year"].astype(str), y=yr["Revenue"], marker_color=ui.THEME["cat"][0],
            text=[f"{ui.format_currency(v)}" for v in yr["Revenue"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=11),
            customdata=yr[["Revenue_Growth_%", "Complete"]].values,
            hovertemplate=("%{x}<br>Revenue ₹%{y:,.0f}<br>Growth %{customdata[0]:.1f}%"
                           "<extra></extra>")))
        fig.update_yaxes(range=[0, yr["Revenue"].max() * 1.22])
        ui.create_plotly_chart(fig, height=320, legend=False, y_title="₹", currency_axis="y",
                               title="Revenue by year")
        if not yr["Complete"].all():
            st.caption("Years that are only partly inside the date filter are shown but are not "
                       "used for the growth KPI.")
    with c2:
        gr = yr.dropna(subset=["Revenue_Growth_%"])
        fig = go.Figure(go.Bar(
            x=gr["Year"].astype(str), y=gr["Revenue_Growth_%"],
            marker_color=[ui.THEME["cat"][2] if v >= 0 else ui.THEME["serious"]
                          for v in gr["Revenue_Growth_%"]],
            text=[f"{v:+.1f}%" for v in gr["Revenue_Growth_%"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=11),
            hovertemplate="%{x}<br>Growth %{y:.2f}%<extra></extra>"))
        ui.create_plotly_chart(fig, height=320, legend=False, y_title="%",
                               title="Year-over-year revenue growth")

# ------------------------------------------------------------------ breakdown
ui.section("Revenue and profit by dimension")

dim_label = st.radio("Break revenue down by", ["Category", "Sub_Category", "Region", "State"],
                     horizontal=True, key="rev_dim",
                     format_func=lambda s: s.replace("_", "-").title())
st.caption(f"Breaking revenue down by **{dim_label.replace('_', '-').lower()}**.")
grp = dl.by_dimension(flt, dim_label)
if ui.validate_dataframe(grp, ["Revenue", "Profit"], f"{dim_label} aggregation"):
    show = grp.head(12).sort_values("Revenue")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=show[dim_label], x=show["Revenue"], name="Revenue", orientation="h",
                         marker_color=ui.THEME["cat"][0], width=0.62,
                         hovertemplate="%{y}<br>Revenue ₹%{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(y=show[dim_label], x=show["Profit"], name="Profit", orientation="h",
                         marker_color=ui.THEME["cat"][2], width=0.34,
                         text=[f"{v:.1f}% margin" for v in show["Margin_%"]],
                         textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(range=[0, show["Revenue"].max() * 1.30])
    ui.create_plotly_chart(fig, height=max(320, 32 * len(show) + 120), x_title="₹",
                           currency_axis="x",
                           title=f"Revenue with profit inside it, by {dim_label.replace('_', '-').lower()}")
    st.caption("The profit bar is drawn inside the revenue bar, so a large but thin-margin "
               "group is obvious without a second axis.")

    with st.expander(f"{dim_label.replace('_', ' ')} table"):
        tbl = grp[[dim_label, "Revenue", "Profit", "Margin_%", "Orders", "Customers",
                   "Quantity", "Revenue_Share_%"]]
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     column_config={
                         "Revenue": st.column_config.NumberColumn(format="₹%.0f"),
                         "Profit": st.column_config.NumberColumn(format="₹%.0f"),
                         "Margin_%": st.column_config.NumberColumn("Margin %", format="%.2f"),
                         "Revenue_Share_%": st.column_config.NumberColumn("Share %",
                                                                          format="%.2f")})
        ui.download_button(tbl, f"revenue_by_{dim_label.lower()}.csv", key="rev_dim_dl")

# -------------------------------------------------------- revenue vs profit
ui.section("Revenue against profit", "Each point is one month in the current selection")
c1, c2 = st.columns([1, 1], gap="medium")
with c1:
    fig = go.Figure(go.Scatter(
        x=m["Revenue"], y=m["Profit"], mode="markers+text", name="Month",
        marker=dict(size=11, color=ui.THEME["cat"][0], line=dict(color=ui.THEME["panel"], width=1)),
        text=[ym if ym.endswith(("-01", "-10")) else "" for ym in m["Year_Month"]],
        textposition="top center", textfont=dict(color=ui.THEME["muted"], size=9),
        customdata=m[["Year_Month", "Margin_%", "Orders"]].values,
        hovertemplate=("%{customdata[0]}<br>Revenue ₹%{x:,.0f}<br>Profit ₹%{y:,.0f}"
                       "<br>Margin %{customdata[1]:.1f}%<br>Orders %{customdata[2]:,.0f}"
                       "<extra></extra>")))
    if len(m) >= 3:
        fit = np.polyfit(m["Revenue"], m["Profit"], 1)
        xs = np.linspace(m["Revenue"].min(), m["Revenue"].max(), 20)
        fig.add_trace(go.Scatter(x=xs, y=np.polyval(fit, xs), mode="lines",
                                 name=f"Trend ({fit[0]:.2f} profit per ₹1 revenue)",
                                 line=dict(color=ui.THEME["muted"], width=1.5, dash="dash"),
                                 hoverinfo="skip"))
    ui.create_plotly_chart(fig, height=360, x_title="Monthly revenue ₹",
                           y_title="Monthly profit ₹", legend=True,
                           title="Monthly revenue vs profit")

with c2:
    band = (dl.delivered(flt).groupby("Discount_Band")
            .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"),
                 Lines=("Order_Line_ID", "count")).reset_index())
    if not band.empty:
        band["Margin_%"] = 100 * band["Profit"] / band["Revenue"]
        order = ["0%", "1-10%", "11-20%", "21-30%", "31-40%"]
        band["Discount_Band"] = pd.Categorical(band["Discount_Band"], order, ordered=True)
        band = band.sort_values("Discount_Band")
        fig = go.Figure(go.Bar(
            x=band["Discount_Band"].astype(str), y=band["Margin_%"],
            marker_color=ui.THEME["cat"][3],
            text=[f"{v:.1f}%" for v in band["Margin_%"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=11),
            customdata=band[["Revenue", "Lines"]].values,
            hovertemplate=("Discount %{x}<br>Margin %{y:.2f}%<br>Revenue ₹%{customdata[0]:,.0f}"
                           "<br>%{customdata[1]:,.0f} lines<extra></extra>")))
        fig.update_yaxes(range=[min(0, band["Margin_%"].min() * 1.2), band["Margin_%"].max() * 1.25])
        ui.create_plotly_chart(fig, height=360, legend=False, y_title="Profit margin %",
                               x_title="Discount band",
                               title="Profit margin by discount band")
        st.caption("An association in observational data, not evidence that discounting causes "
                   "the loss - the products that get discounted may differ systematically.")

# ---------------------------------------------------------------- drivers
ui.section("Revenue drivers", "Read from the Step 10 SQL findings - nothing here is generic")
findings = dl.load_table("sql_key_findings")
if findings is not None and {"Area", "Finding (computed by SQL)"} <= set(findings.columns):
    keep = ["Revenue", "Growth", "Customer concentration", "Repeat purchasing", "Categories",
            "Discounts", "Returns / cancellations"]
    sub = findings[findings["Area"].isin(keep)]
    for _, row in sub.iterrows():
        ui.panel(f'<h4 style="font-size:0.9rem;color:{ui.THEME["cat"][0]}">{row["Area"]}</h4>'
                 f'<p>{row["Finding (computed by SQL)"]}</p>'
                 f'<p class="note">Source query: {row.get("Source query", "-")}</p>')
    st.caption("These are full-period findings computed in SQL (Step 10). They do not change with "
               "the filters above, which is why they are shown separately from the charts.")
else:
    st.info("The Step 10 findings table (`outputs/tables/sql_key_findings.csv`) was not found, "
            "so the driver panel is unavailable. The charts above are unaffected.")
