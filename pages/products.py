"""PRODUCT ANALYTICS - which products earn, which only turn over."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Product Analytics",
               "Revenue, margin, volume, discounting and returns by category, sub-category and "
               "product.", "📦")

sales = dl.load_sales()
if not ui.validate_dataframe(sales, ["Sales", "Profit", "Category", "Product_Name", "Quantity"],
                             "Transaction data"):
    st.stop()

flt = ui.sales_filters(sales, key="prod", fields=("date", "region", "category", "sub_category"))
ui.active_filter_note(flt, sales)
if flt.empty:
    st.warning("No order lines match the current filters.")
    st.stop()

k = dl.kpis(flt)
d = dl.delivered(flt)
cat = dl.by_dimension(flt, "Category")

ui.kpi_row([
    dict(title="Revenue", value=ui.format_currency(k["revenue"]),
         subtitle=f"{d['Product_ID'].nunique()} products sold", accent=ui.THEME["cat"][0]),
    dict(title="Profit", value=ui.format_currency(k["profit"]),
         subtitle=f"Margin {ui.format_percentage(k['margin'])}", accent=ui.THEME["cat"][2]),
    dict(title="Units sold", value=ui.format_number(k["quantity"]),
         subtitle=f"{k['qty_per_order']:.2f} per order", accent=ui.THEME["cat"][6]),
    dict(title="Best margin category",
         value=str(cat.loc[cat["Margin_%"].idxmax(), "Category"]) if not cat.empty else "-",
         subtitle=f"{cat['Margin_%'].max():.1f}% margin" if not cat.empty else "",
         accent=ui.THEME["cat"][2]),
    dict(title="Largest category",
         value=str(cat.loc[cat["Revenue"].idxmax(), "Category"]) if not cat.empty else "-",
         subtitle=f"{cat['Revenue_Share_%'].max():.1f}% of revenue" if not cat.empty else "",
         accent=ui.THEME["cat"][3]),
    dict(title="Booked value lost", value=ui.format_percentage(k["not_realised"]),
         subtitle="Returns and cancellations", accent=ui.THEME["warning"]),
], per_row=6)

# ----------------------------------------------------------------- categories
ui.section("Category performance", "Revenue, profit and volume together - size never hides margin")

c1, c2 = st.columns([1.25, 1], gap="medium")
with c1:
    s = cat.sort_values("Revenue")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=s["Category"], x=s["Revenue"], name="Revenue", orientation="h",
                         marker_color=ui.THEME["cat"][0], width=0.62,
                         hovertemplate="%{y}<br>Revenue ₹%{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(y=s["Category"], x=s["Profit"], name="Profit", orientation="h",
                         marker_color=ui.THEME["cat"][2], width=0.34,
                         text=[f"{v:.1f}% margin" for v in s["Margin_%"]], textposition="outside",
                         textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(range=[0, s["Revenue"].max() * 1.32])
    ui.create_plotly_chart(fig, height=360, x_title="₹", currency_axis="x",
                           title="Revenue and profit by category")
with c2:
    s = cat.sort_values("Quantity")
    fig = go.Figure(go.Bar(
        x=s["Quantity"], y=s["Category"], orientation="h", marker_color=ui.THEME["cat"][6],
        text=[f"{int(v):,}" for v in s["Quantity"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=s[["Revenue", "Orders"]].values,
        hovertemplate=("%{y}<br>%{x:,.0f} units<br>Revenue ₹%{customdata[0]:,.0f}"
                       "<br>%{customdata[1]:,.0f} orders<extra></extra>")))
    fig.update_xaxes(range=[0, s["Quantity"].max() * 1.28])
    ui.create_plotly_chart(fig, height=360, legend=False, x_title="Units",
                           title="Units sold by category")

# ------------------------------------------------------------------ products
prod = (d.groupby(["Product_ID", "Product_Name", "Category", "Sub_Category"])
          .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Quantity=("Quantity", "sum"),
               Orders=("Order_ID", "nunique"),
               Avg_Discount=("Discount", "mean")).reset_index())
prod["Margin_%"] = 100 * prod["Profit"] / prod["Revenue"]
cat_margin = prod.groupby("Category").apply(
    lambda g: 100 * g["Profit"].sum() / g["Revenue"].sum(), include_groups=False)
prod["Category_Margin_%"] = prod["Category"].map(cat_margin)
prod["Margin_vs_Category_pp"] = prod["Margin_%"] - prod["Category_Margin_%"]
prod["Avg_Discount_%"] = 100 * prod["Avg_Discount"]

all_lines = flt.groupby("Product_ID").size().rename("All_Lines")
delivered_lines = d.groupby("Product_ID").size().rename("Delivered_Lines")
rates = pd.concat([all_lines, delivered_lines], axis=1).fillna(0)
rates["Return_Cancel_Rate_%"] = 100 * (1 - rates["Delivered_Lines"] / rates["All_Lines"])
prod = prod.merge(rates[["Return_Cancel_Rate_%"]], left_on="Product_ID", right_index=True,
                  how="left")

ui.section("Products", "Ranked on the current selection")
c1, c2 = st.columns(2, gap="medium")
with c1:
    top = prod.nlargest(10, "Revenue").sort_values("Revenue")
    fig = go.Figure(go.Bar(
        x=top["Revenue"], y=top["Product_Name"].str.slice(0, 30), orientation="h",
        marker_color=ui.THEME["cat"][0],
        text=[f"{v:.1f}% margin" for v in top["Margin_%"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=top[["Category", "Quantity", "Profit"]].values,
        hovertemplate=("%{y}<br>Revenue ₹%{x:,.0f}<br>%{customdata[0]}"
                       "<br>%{customdata[1]:,.0f} units<br>Profit ₹%{customdata[2]:,.0f}"
                       "<extra></extra>")))
    fig.update_xaxes(range=[0, top["Revenue"].max() * 1.30])
    ui.create_plotly_chart(fig, height=400, legend=False, x_title="₹", currency_axis="x",
                           title="Top 10 products by revenue")
with c2:
    bottom = prod.nsmallest(10, "Margin_vs_Category_pp").sort_values("Margin_vs_Category_pp",
                                                                     ascending=False)
    fig = go.Figure(go.Bar(
        x=bottom["Margin_vs_Category_pp"], y=bottom["Product_Name"].str.slice(0, 30),
        orientation="h",
        marker_color=[ui.THEME["critical"] if v < -10 else ui.THEME["serious"]
                      for v in bottom["Margin_vs_Category_pp"]],
        text=[f"{v:.1f} pp" for v in bottom["Margin_vs_Category_pp"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=bottom[["Margin_%", "Category_Margin_%", "Revenue"]].values,
        hovertemplate=("%{y}<br>Margin %{customdata[0]:.1f}% vs category %{customdata[1]:.1f}%"
                       "<br>Revenue ₹%{customdata[2]:,.0f}<extra></extra>")))
    fig.update_xaxes(range=[bottom["Margin_vs_Category_pp"].min() * 1.12, 4])
    ui.create_plotly_chart(fig, height=400, legend=False,
                           x_title="Percentage points vs the product's own category margin",
                           title="Bottom 10 products by margin against their category")
    st.caption("A defined metric, not a vague 'worst' list: each product's margin minus the "
               "margin of the category it sits in.")

# ------------------------------------------------------------------- scatter
ui.section("Revenue against profit", "Bubble size = units sold · colour = category")
fig = go.Figure()
for i, (name, grp) in enumerate(prod.groupby("Category")):
    fig.add_trace(go.Scatter(
        x=grp["Revenue"], y=grp["Profit"], mode="markers", name=str(name),
        marker=dict(size=np.sqrt(grp["Quantity"]) * 1.6 + 6, color=ui.THEME["cat"][i % 8],
                    opacity=0.85, line=dict(width=1, color=ui.THEME["panel"])),
        customdata=grp[["Product_Name", "Quantity", "Margin_%", "Avg_Discount_%",
                        "Return_Cancel_Rate_%"]].values,
        hovertemplate=("<b>%{customdata[0]}</b><br>Revenue ₹%{x:,.0f}<br>Profit ₹%{y:,.0f}"
                       "<br>%{customdata[1]:,.0f} units<br>Margin %{customdata[2]:.1f}%"
                       "<br>Avg discount %{customdata[3]:.1f}%"
                       "<br>Return/cancel %{customdata[4]:.1f}%<extra>" + str(name) +
                       "</extra>")))
fig.add_hline(y=0, line_dash="dash", line_color=ui.THEME["muted"])
for _, r in prod.nlargest(3, "Revenue").iterrows():
    fig.add_annotation(x=r["Revenue"], y=r["Profit"], text=r["Product_Name"][:24],
                       showarrow=False, yshift=16, font=dict(color=ui.THEME["ink"], size=10))
worst = prod.nsmallest(1, "Profit")
if not worst.empty:
    w = worst.iloc[0]
    fig.add_annotation(x=w["Revenue"], y=w["Profit"], text=f"{w['Product_Name'][:24]} "
                                                           f"({w['Margin_%']:.1f}%)",
                       showarrow=False, yshift=-18, font=dict(color=ui.THEME["warning"], size=10))
ui.create_plotly_chart(fig, height=520, x_title="Revenue ₹", y_title="Profit ₹",
                       title="Revenue vs profit by product (points below the line lose money)")
st.caption("Colour carries the category, but every point also names itself, its margin and its "
           "discount on hover, so the chart never depends on colour alone.")

# ----------------------------------------------------------------- discounting
ui.section("Discounting and returns")
c1, c2 = st.columns(2, gap="medium")
with c1:
    band = (d.groupby(["Category", "Discount_Band"])
              .agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum")).reset_index())
    band["Margin_%"] = 100 * band["Profit"] / band["Revenue"]
    order = ["0%", "1-10%", "11-20%", "21-30%", "31-40%"]
    band["Discount_Band"] = pd.Categorical(band["Discount_Band"], order, ordered=True)
    band = band.sort_values("Discount_Band")
    fig = go.Figure()
    for i, (name, grp) in enumerate(band.groupby("Category")):
        fig.add_trace(go.Scatter(
            x=grp["Discount_Band"].astype(str), y=grp["Margin_%"], mode="lines+markers",
            name=str(name), line=dict(color=ui.THEME["cat"][i % 8], width=2),
            marker=dict(size=7),
            hovertemplate="%{x}<br>%{y:.1f}% margin<extra>" + str(name) + "</extra>"))
    fig.add_hline(y=0, line_dash="dot", line_color=ui.THEME["muted"])
    ui.create_plotly_chart(fig, height=380, y_title="Profit margin %", x_title="Discount band",
                           title="Margin by discount band, within each category")
    st.caption("An association in observational data - it does not establish that discounting "
               "causes the margin loss.")
with c2:
    lost = (flt.groupby("Category")
            .apply(lambda g: pd.Series({
                "Booked": g["Booked_Value"].sum(),
                "Delivered": g.loc[g["Is_Delivered"] == 1, "Sales"].sum()}),
                include_groups=False).reset_index())
    lost["Lost_%"] = 100 * (1 - lost["Delivered"] / lost["Booked"])
    lost = lost.sort_values("Lost_%")
    fig = go.Figure(go.Bar(
        x=lost["Lost_%"], y=lost["Category"], orientation="h",
        marker_color=[ui.THEME["critical"] if v > 12 else ui.THEME["cat"][1]
                      for v in lost["Lost_%"]],
        text=[f"{v:.1f}%" for v in lost["Lost_%"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=(lost["Booked"] - lost["Delivered"]).values,
        hovertemplate="%{y}<br>%{x:.2f}% of booked value lost<br>₹%{customdata:,.0f}<extra></extra>"))
    fig.update_xaxes(range=[0, lost["Lost_%"].max() * 1.3])
    ui.create_plotly_chart(fig, height=380, legend=False,
                           x_title="% of booked value lost to returns and cancellations",
                           title="Booked value not realised, by category")

# --------------------------------------------------------- performance matrix
ui.section("Product performance matrix", "Sortable and filterable")
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    pick_cat = st.multiselect("Category", sorted(prod["Category"].unique()), default=[],
                              placeholder="All", key="prod_matrix_cat")
with c2:
    min_rev = st.number_input("Minimum revenue (₹)", min_value=0,
                              value=0, step=100000, key="prod_matrix_rev")
with c3:
    sort_by = st.selectbox("Sort by", ["Revenue", "Profit", "Margin_%", "Quantity",
                                       "Return_Cancel_Rate_%", "Margin_vs_Category_pp"],
                           key="prod_matrix_sort")

matrix = prod.copy()
if pick_cat:
    matrix = matrix[matrix["Category"].isin(pick_cat)]
matrix = matrix[matrix["Revenue"] >= min_rev].sort_values(sort_by, ascending=False)
show = matrix[["Product_ID", "Product_Name", "Category", "Sub_Category", "Revenue", "Profit",
               "Quantity", "Margin_%", "Avg_Discount_%", "Return_Cancel_Rate_%",
               "Margin_vs_Category_pp"]]
st.dataframe(show, use_container_width=True, hide_index=True, height=420,
             column_config={
                 "Product_Name": st.column_config.TextColumn("Product", width="medium"),
                 "Revenue": st.column_config.NumberColumn(format="₹%.0f"),
                 "Profit": st.column_config.NumberColumn(format="₹%.0f"),
                 "Margin_%": st.column_config.NumberColumn("Margin %", format="%.2f"),
                 "Avg_Discount_%": st.column_config.NumberColumn("Avg discount %", format="%.1f"),
                 "Return_Cancel_Rate_%": st.column_config.NumberColumn("Return/cancel %",
                                                                        format="%.1f"),
                 "Margin_vs_Category_pp": st.column_config.NumberColumn("vs category (pp)",
                                                                         format="%.1f")})
st.caption(f"{len(show)} of {len(prod)} products shown.")
ui.download_button(show, "product_performance_matrix.csv", key="prod_matrix_dl")

flagged = dl.load_table("prod_investigate", subdir="sql")
if flagged is not None:
    with st.expander("Products flagged for investigation by the Step 10 rules"):
        st.dataframe(flagged, use_container_width=True, hide_index=True)
        st.caption("Rule: a product whose margin is under half its category's, or whose "
                   "return/cancel rate is more than 1.5x the overall rate. Computed in SQL over "
                   "the full period, so it does not respond to the filters above.")
