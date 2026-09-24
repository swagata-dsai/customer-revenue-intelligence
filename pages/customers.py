"""CUSTOMER INTELLIGENCE - value distribution, top customers, recency and frequency."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Customer Intelligence",
               "Who the customers are, what they are worth, and how recently they bought. "
               "Customers are identified by Customer_ID only - no names are published.", "👥")

sales = dl.load_sales()
customers = dl.load_customers()
if not ui.validate_dataframe(sales, ["Sales", "Customer_ID"], "Transaction data"):
    st.stop()
if not ui.validate_dataframe(customers, ["Customer_ID", "RFM_Segment"], "Customer dimension"):
    st.stop()

flt = ui.sales_filters(sales, key="cust", fields=("date", "region", "category", "segment"))
ui.active_filter_note(flt, sales)
if flt.empty:
    st.warning("No order lines match the current filters.")
    st.stop()

k = dl.kpis(flt)
roll = dl.customer_rollup(flt)
scored = customers[customers.get("Has_Delivered_Order", 1) == 1].copy()
in_scope = scored[scored["Customer_ID"].isin(roll["Customer_ID"])]

has_clv = "Estimated_12M_Future_Profit" in customers.columns

# ------------------------------------------------------------------ KPI cards
cards = [
    dict(title="Total customers", value=ui.format_number(k["customers"]),
         subtitle=f"Of {len(customers):,} registered", accent=ui.THEME["cat"][6]),
    dict(title="Avg customer revenue", value=ui.format_currency(k["revenue_per_customer"],
                                                                unit="inr"),
         subtitle="Revenue ÷ customers in the selection", accent=ui.THEME["cat"][0]),
    dict(title="Average order value", value=ui.format_currency(k["aov"], unit="inr"),
         subtitle=f"{k['orders']:,} orders", accent=ui.THEME["cat"][3]),
    dict(title="Avg frequency", value=f"{in_scope['Frequency_Orders'].mean():.2f}"
         if "Frequency_Orders" in in_scope.columns and not in_scope.empty else "-",
         subtitle="Lifetime delivered orders per customer", accent=ui.THEME["cat"][4]),
    dict(title="Avg recency", value=f"{in_scope['Recency_Days'].mean():.0f} days"
         if "Recency_Days" in in_scope.columns and not in_scope.empty else "-",
         subtitle=f"At the {dl.REFERENCE_DATE} snapshot", accent=ui.THEME["cat"][1]),
]
if has_clv and not in_scope.empty:
    cards.append(dict(
        title="Est. 12-month profit", value=ui.format_currency(
            in_scope["Estimated_12M_Future_Profit"].sum()),
        subtitle="Step 7 estimate, not actual revenue", accent=ui.THEME["cat"][2]))
ui.kpi_row(cards)

st.caption(f"Frequency, recency and customer-value figures are the Step 5-7 snapshot at "
           f"{dl.REFERENCE_DATE} for the customers in the current selection. Revenue, orders "
           f"and AOV are computed from the filtered transactions.")

# ------------------------------------------------------------- distributions
ui.section("How customer value is distributed")

c1, c2 = st.columns(2, gap="medium")
with c1:
    fig = go.Figure(go.Histogram(
        x=roll["Revenue"], nbinsx=45, marker_color=ui.THEME["cat"][0],
        hovertemplate="Revenue ₹%{x:,.0f}<br>%{y} customers<extra></extra>"))
    med = roll["Revenue"].median()
    fig.add_vline(x=med, line_dash="dash", line_color=ui.THEME["warning"],
                  annotation_text=f"median {ui.format_currency(med, unit='inr')}",
                  annotation_font_color=ui.THEME["warning"], annotation_font_size=11)
    ui.create_plotly_chart(fig, height=340, legend=False, x_title="Revenue per customer ₹",
                           y_title="Customers", currency_axis="x",
                           title="Customer revenue distribution")
    st.caption(f"Mean {ui.format_currency(roll['Revenue'].mean(), unit='inr')} against a median "
               f"of {ui.format_currency(med, unit='inr')}: the distribution has a long right tail, "
               f"so the mean sits well above the typical customer.")

with c2:
    bands = pd.cut(roll["Orders"], bins=[0, 1, 3, 6, 10, np.inf],
                   labels=["1 order", "2-3 orders", "4-6 orders", "7-10 orders", "11+ orders"])
    freq = (roll.assign(Band=bands).groupby("Band", observed=True)
            .agg(Customers=("Customer_ID", "count"), Revenue=("Revenue", "sum")).reset_index())
    freq["Customer_%"] = 100 * freq["Customers"] / freq["Customers"].sum()
    freq["Revenue_%"] = 100 * freq["Revenue"] / freq["Revenue"].sum()
    fig = go.Figure()
    fig.add_trace(go.Bar(x=freq["Band"].astype(str), y=freq["Customer_%"], name="% of customers",
                         marker_color=ui.THEME["cat"][4],
                         hovertemplate="%{x}<br>%{y:.1f}% of customers<extra></extra>"))
    fig.add_trace(go.Bar(x=freq["Band"].astype(str), y=freq["Revenue_%"], name="% of revenue",
                         marker_color=ui.THEME["cat"][0],
                         hovertemplate="%{x}<br>%{y:.1f}% of revenue<extra></extra>"))
    fig.update_layout(barmode="group")
    ui.create_plotly_chart(fig, height=340, y_title="%", title="Orders per customer")

c1, c2 = st.columns(2, gap="medium")
with c1:
    if "Recency_Band" in in_scope.columns and not in_scope.empty:
        rb = (in_scope.groupby(["Recency_Band_Order", "Recency_Band"], observed=True)
              .size().reset_index(name="Customers").sort_values("Recency_Band_Order"))
    else:
        rb = pd.DataFrame()
    if not rb.empty:
        colours = [ui.THEME["cat"][2], ui.THEME["cat"][2], ui.THEME["cat"][0],
                   ui.THEME["warning"], ui.THEME["critical"], ui.THEME["muted"]]
        fig = go.Figure(go.Bar(
            x=rb["Recency_Band"], y=rb["Customers"], marker_color=colours[:len(rb)],
            text=[f"{v:,}" for v in rb["Customers"]], textposition="outside",
            textfont=dict(color=ui.THEME["ink"], size=11),
            hovertemplate="%{x}<br>%{y:,} customers<extra></extra>"))
        fig.update_yaxes(range=[0, rb["Customers"].max() * 1.2])
        ui.create_plotly_chart(fig, height=340, legend=False, y_title="Customers",
                               x_title=f"Days since last delivered purchase at {dl.REFERENCE_DATE}",
                               title="Recency distribution")
        st.caption("Green and blue are active (under 180 days, the Step 7 threshold); amber and "
                   "red are **inactive**, never 'churned' - no churn event is defined in this "
                   "project.")

with c2:
    pareto = roll.sort_values("Revenue", ascending=False).reset_index(drop=True)
    pareto["cum_rev_%"] = 100 * pareto["Revenue"].cumsum() / pareto["Revenue"].sum()
    pareto["cum_cust_%"] = 100 * (pareto.index + 1) / len(pareto)
    fig = go.Figure(go.Scatter(
        x=pareto["cum_cust_%"], y=pareto["cum_rev_%"], mode="lines",
        line=dict(color=ui.THEME["cat"][2], width=2.6), name="Cumulative revenue",
        hovertemplate="Top %{x:.1f}% of customers<br>%{y:.1f}% of revenue<extra></extra>"))
    for mark in (10, 20, 50):
        if mark <= 100:
            y = float(np.interp(mark, pareto["cum_cust_%"], pareto["cum_rev_%"]))
            fig.add_trace(go.Scatter(x=[mark], y=[y], mode="markers+text",
                                     marker=dict(size=10, color=ui.THEME["cat"][3]),
                                     text=[f" top {mark}% → {y:.1f}%"], textposition="middle right",
                                     textfont=dict(color=ui.THEME["ink"], size=10),
                                     showlegend=False, hoverinfo="skip"))
    fig.update_xaxes(range=[0, 100]); fig.update_yaxes(range=[0, 104])
    ui.create_plotly_chart(fig, height=340, legend=False, x_title="% of customers",
                           y_title="% of revenue", title="Revenue concentration (Pareto)")

# --------------------------------------------------------------- top customers
ui.section("Top customers", "Ranked on the filtered transactions")

metric = st.radio("Rank by", ["Revenue", "Profit"], horizontal=True, key="cust_metric")
top_n = st.slider("How many customers", 5, 50, 15, step=5, key="cust_topn")
top = roll.nlargest(top_n, metric).copy()
join_cols = [c for c in ["Customer_ID", "RFM_Segment", "Cluster_Label", "Recency_Days",
                         "Frequency_Orders", "Monetary_Revenue", "Estimated_12M_Future_Profit",
                         "Illustrative_3Y_Value", "Home_Region", "Age_Band"]
             if c in customers.columns]
top = top.merge(customers[join_cols], on="Customer_ID", how="left")

c1, c2 = st.columns([1.15, 1], gap="medium")
with c1:
    chart = top.head(15).sort_values(metric)
    fig = go.Figure(go.Bar(
        x=chart[metric], y=chart["Customer_ID"], orientation="h",
        marker_color=ui.THEME["cat"][0] if metric == "Revenue" else ui.THEME["cat"][2],
        text=[ui.format_currency(v, unit="inr") for v in chart[metric]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=chart[["Orders", "RFM_Segment"]].values if "RFM_Segment" in chart.columns
        else chart[["Orders", "Orders"]].values,
        hovertemplate=("%{y}<br>" + metric + " ₹%{x:,.0f}<br>Orders %{customdata[0]}"
                       "<br>Segment %{customdata[1]}<extra></extra>")))
    fig.update_xaxes(range=[0, chart[metric].max() * 1.30])
    ui.create_plotly_chart(fig, height=max(340, 26 * len(chart) + 110), legend=False,
                           x_title="₹", currency_axis="x",
                           title=f"Top {len(chart)} customers by {metric.lower()}")
with c2:
    share = 100 * top[metric].sum() / roll[metric].sum() if roll[metric].sum() else float("nan")
    ui.panel(
        f'<h4>What the top {top_n} carry</h4>'
        f'<p>They hold <strong>{share:.1f}%</strong> of the {metric.lower()} in this selection, '
        f'from {100 * top_n / len(roll):.1f}% of its customers.</p>'
        f'<p class="note">Revenue concentration is the single most repeated finding in this '
        f'project: it means retention of a small group matters more than acquisition volume.</p>')
    seg_mix = (top["RFM_Segment"].value_counts().rename_axis("Segment")
               .reset_index(name="Customers")) if "RFM_Segment" in top.columns else pd.DataFrame()
    if not seg_mix.empty:
        fig = go.Figure(go.Bar(
            x=seg_mix["Customers"], y=seg_mix["Segment"], orientation="h",
            marker_color=ui.THEME["cat"][4],
            hovertemplate="%{y}<br>%{x} of the top customers<extra></extra>"))
        ui.create_plotly_chart(fig, height=230, legend=False, x_title="Customers in the top list",
                               title="Which segments the top customers sit in")

table_cols = [c for c in ["Customer_ID", "Revenue", "Profit", "Orders", "Quantity",
                          "Recency_Days", "Frequency_Orders", "Monetary_Revenue", "RFM_Segment",
                          "Cluster_Label", "Estimated_12M_Future_Profit", "Illustrative_3Y_Value"]
              if c in top.columns]
st.dataframe(top[table_cols], use_container_width=True, hide_index=True,
             column_config={
                 "Revenue": st.column_config.NumberColumn("Revenue (selection)", format="₹%.0f"),
                 "Profit": st.column_config.NumberColumn("Profit (selection)", format="₹%.0f"),
                 "Monetary_Revenue": st.column_config.NumberColumn("Lifetime revenue",
                                                                   format="₹%.0f"),
                 "Estimated_12M_Future_Profit": st.column_config.NumberColumn(
                     "Est. next-12m profit", format="₹%.0f"),
                 "Illustrative_3Y_Value": st.column_config.NumberColumn("Illustrative 3Y value",
                                                                        format="₹%.0f"),
                 "Recency_Days": st.column_config.NumberColumn("Recency (days)"),
                 "Frequency_Orders": st.column_config.NumberColumn("Frequency (orders)")})
ui.download_button(top[table_cols], "top_customers.csv", key="cust_top_dl")

# ------------------------------------------------------------ customer lookup
ui.section("Customer lookup", "Select a Customer_ID to see everything the project holds on them")

options = roll["Customer_ID"].tolist()
picked = st.selectbox("Customer_ID", options, index=0 if options else None, key="cust_pick")
if picked:
    st.caption(f"Selected customer: **{picked}** — figures below use the current filters; the "
               f"RFM, cluster and customer-value fields are the {dl.REFERENCE_DATE} snapshot.")
    row = customers[customers["Customer_ID"] == picked]
    sel = roll[roll["Customer_ID"] == picked].iloc[0]
    lines = flt[(flt["Customer_ID"] == picked) & (flt["Is_Delivered"] == 1)]

    detail = []
    detail.append(dict(title="Revenue (selection)", value=ui.format_currency(sel["Revenue"],
                                                                             unit="inr"),
                       subtitle=f"{int(sel['Orders'])} orders, {int(sel['Quantity'])} units",
                       accent=ui.THEME["cat"][0]))
    detail.append(dict(title="Profit (selection)", value=ui.format_currency(sel["Profit"],
                                                                            unit="inr"),
                       subtitle=f"Margin {100 * sel['Profit'] / sel['Revenue']:.1f}%"
                       if sel["Revenue"] else "-", accent=ui.THEME["cat"][2]))
    if not row.empty:
        r = row.iloc[0]
        detail.append(dict(title="Recency / frequency",
                           value=f"{int(r['Recency_Days'])}d · {int(r['Frequency_Orders'])}",
                           subtitle=f"Snapshot at {dl.REFERENCE_DATE}", accent=ui.THEME["cat"][1]))
        detail.append(dict(title="Monetary (lifetime)",
                           value=ui.format_currency(r["Monetary_Revenue"], unit="inr"),
                           subtitle="All delivered orders to date", accent=ui.THEME["cat"][0]))
        detail.append(dict(title="RFM segment", value=str(r["RFM_Segment"]),
                           subtitle=f"K-Means cluster: {r.get('Cluster_Label', '-')}",
                           accent=ui.THEME["cat"][4]))
        if has_clv and pd.notna(r.get("Estimated_12M_Future_Profit")):
            detail.append(dict(title="Est. next-12m profit",
                               value=ui.format_currency(r["Estimated_12M_Future_Profit"],
                                                        unit="inr"),
                               subtitle=f"{r.get('Estimate_Method', 'Step 7 estimate')}",
                               accent=ui.THEME["cat"][2]))
    ui.kpi_row(detail)

    if not lines.empty:
        c1, c2 = st.columns([1.4, 1], gap="medium")
        with c1:
            mm = lines.groupby("Year_Month")["Sales"].sum().reset_index()
            fig = go.Figure(go.Bar(x=mm["Year_Month"], y=mm["Sales"],
                                   marker_color=ui.THEME["cat"][0],
                                   hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"))
            ui.create_plotly_chart(fig, height=300, legend=False, y_title="₹", currency_axis="y",
                                   title=f"{picked} · revenue by month")
        with c2:
            cc = lines.groupby("Category")["Sales"].sum().sort_values().reset_index()
            fig = go.Figure(go.Bar(x=cc["Sales"], y=cc["Category"], orientation="h",
                                   marker_color=ui.THEME["cat"][3],
                                   hovertemplate="%{y}<br>₹%{x:,.0f}<extra></extra>"))
            ui.create_plotly_chart(fig, height=300, legend=False, x_title="₹", currency_axis="x",
                                   title="Category mix")
        with st.expander(f"Recent delivered orders for {picked}"):
            orders = (lines.groupby(["Order_ID", "Order_Date"])
                      .agg(Lines=("Order_Line_ID", "count"), Revenue=("Sales", "sum"),
                           Profit=("Profit", "sum")).reset_index()
                      .sort_values("Order_Date", ascending=False).head(15))
            orders["Order_Date"] = orders["Order_Date"].dt.date
            st.dataframe(orders, use_container_width=True, hide_index=True,
                         column_config={
                             "Revenue": st.column_config.NumberColumn(format="₹%.0f"),
                             "Profit": st.column_config.NumberColumn(format="₹%.0f")})
