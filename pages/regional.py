"""REGIONAL ANALYTICS - regional performance and the category mix behind it."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Regional Analytics",
               "How each region performs, and what its category mix explains.", "🌍")

sales = dl.load_sales()
if not ui.validate_dataframe(sales, ["Sales", "Region", "State", "City"], "Transaction data"):
    st.stop()

flt = ui.sales_filters(sales, key="reg", fields=("date", "region", "category", "segment"))
ui.active_filter_note(flt, sales)
if flt.empty:
    st.warning("No order lines match the current filters.")
    st.stop()

reg = dl.by_dimension(flt, "Region")
if not ui.validate_dataframe(reg, ["Revenue"], "Regional aggregation"):
    st.stop()

ui.kpi_row([
    dict(title="Regions", value=str(len(reg)), subtitle="Business regions in the selection",
         accent=ui.THEME["cat"][0]),
    dict(title="Largest by revenue", value=str(reg.iloc[0]["Region"]),
         subtitle=f"{ui.format_currency(reg.iloc[0]['Revenue'])} · "
                  f"{reg.iloc[0]['Revenue_Share_%']:.1f}% of the selection",
         accent=ui.THEME["cat"][0]),
    dict(title="Best margin", value=str(reg.loc[reg["Margin_%"].idxmax(), "Region"]),
         subtitle=f"{reg['Margin_%'].max():.2f}% profit margin", accent=ui.THEME["cat"][2]),
    dict(title="Highest AOV", value=str(reg.loc[reg["AOV"].idxmax(), "Region"]),
         subtitle=f"{ui.format_currency(reg['AOV'].max(), unit='inr')} per order",
         accent=ui.THEME["cat"][3]),
    dict(title="Most customers", value=str(reg.loc[reg["Customers"].idxmax(), "Region"]),
         subtitle=f"{int(reg['Customers'].max()):,} customers", accent=ui.THEME["cat"][6]),
], per_row=5)

# ----------------------------------------------------- why no map (or a map)
cities = flt[["City", "State", "Region"]].drop_duplicates()
ui.panel(
    f'<h4>Ranked bars rather than a map - and why</h4>'
    f'<p>The geography in this dataset is a customer&rsquo;s home city: {len(cities)} cities '
    f'mapped to {flt["Region"].nunique()} business regions. There are no latitude and longitude '
    f'columns, no postal codes and no store locations, and the regions are business groupings '
    f'rather than official administrative boundaries.</p>'
    f'<p class="note">A filled map would either need the city names geocoded at run time or would '
    f'shade areas the data does not actually describe, so this page uses ranked bars and a '
    f'region x category matrix. They answer the same questions without the risk.</p>')

# ----------------------------------------------------------------- performance
ui.section("Regional performance")
c1, c2 = st.columns([1.2, 1], gap="medium")
with c1:
    s = reg.sort_values("Revenue")
    fig = go.Figure()
    fig.add_trace(go.Bar(y=s["Region"], x=s["Revenue"], name="Revenue", orientation="h",
                         marker_color=ui.THEME["cat"][0], width=0.62,
                         hovertemplate="%{y}<br>Revenue ₹%{x:,.0f}<extra></extra>"))
    fig.add_trace(go.Bar(y=s["Region"], x=s["Profit"], name="Profit", orientation="h",
                         marker_color=ui.THEME["cat"][2], width=0.34,
                         text=[f"{v:.1f}% margin" for v in s["Margin_%"]], textposition="outside",
                         textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(range=[0, s["Revenue"].max() * 1.32])
    ui.create_plotly_chart(fig, height=360, x_title="₹", currency_axis="x",
                           title="Revenue and profit by region")
with c2:
    s = reg.sort_values("Revenue", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s["Region"], y=s["Customers"], name="Customers",
                         marker_color=ui.THEME["cat"][6],
                         hovertemplate="%{x}<br>%{y:,} customers<extra></extra>"))
    fig.add_trace(go.Bar(x=s["Region"], y=s["Orders"], name="Orders",
                         marker_color=ui.THEME["cat"][0],
                         hovertemplate="%{x}<br>%{y:,} orders<extra></extra>"))
    fig.update_layout(barmode="group")
    ui.create_plotly_chart(fig, height=360, y_title="Count",
                           title="Customers and orders by region")
    st.caption("Both series are counts, so they belong on the same axis.")

c1, c2 = st.columns(2, gap="medium")
with c1:
    s = reg.sort_values("AOV", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=s["Region"], y=s["AOV"], name="Average order value",
                         marker_color=ui.THEME["cat"][3],
                         text=[ui.format_currency(v, unit="inr") for v in s["AOV"]],
                         textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{x}<br>AOV ₹%{y:,.0f}<extra></extra>"))
    rev_per_cust = s["Revenue"] / s["Customers"]
    fig.add_trace(go.Bar(x=s["Region"], y=rev_per_cust, name="Revenue per customer",
                         marker_color=ui.THEME["cat"][0],
                         text=[ui.format_currency(v, unit="inr") for v in rev_per_cust],
                         textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                         hovertemplate="%{x}<br>₹%{y:,.0f} per customer<extra></extra>"))
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, rev_per_cust.max() * 1.25])
    ui.create_plotly_chart(fig, height=360, y_title="₹", currency_axis="y",
                           title="Average order value and revenue per customer")
with c2:
    state = dl.by_dimension(flt, "State").head(10).sort_values("Revenue")
    fig = go.Figure(go.Bar(
        x=state["Revenue"], y=state["State"], orientation="h", marker_color=ui.THEME["cat"][4],
        text=[ui.format_currency(v) for v in state["Revenue"]], textposition="outside",
        textfont=dict(color=ui.THEME["ink"], size=10),
        customdata=state[["Margin_%", "Customers"]].values,
        hovertemplate=("%{y}<br>Revenue ₹%{x:,.0f}<br>Margin %{customdata[0]:.1f}%"
                       "<br>%{customdata[1]:,} customers<extra></extra>")))
    fig.update_xaxes(range=[0, state["Revenue"].max() * 1.35])
    ui.create_plotly_chart(fig, height=360, legend=False, x_title="₹", currency_axis="x",
                           title="Top 10 states by revenue")

# ------------------------------------------------------------------- matrix
ui.section("Region x category", "Every cell shows its number - colour is only a reading aid")
d = dl.delivered(flt)
piv_rev = d.pivot_table(index="Category", columns="Region", values="Sales", aggfunc="sum")
piv_pro = d.pivot_table(index="Category", columns="Region", values="Profit", aggfunc="sum")
view = st.radio("Show", ["Profit margin %", "Revenue"], horizontal=True, key="reg_matrix_view")

if not piv_rev.empty:
    if view == "Profit margin %":
        z = (100 * piv_pro / piv_rev)
        text = z.round(1).astype(str)
        hover = "Category %{y}<br>Region %{x}<br>Margin %{z:.2f}%<extra></extra>"
    else:
        z = piv_rev / 1e5
        text = z.round(1).astype(str)
        hover = "Category %{y}<br>Region %{x}<br>Revenue ₹%{z:,.1f} lakh<extra></extra>"
    order = piv_rev.sum(axis=1).sort_values(ascending=False).index
    z = z.reindex(order); text = text.reindex(order)
    fig = go.Figure(go.Heatmap(
        z=z.values, x=list(z.columns), y=list(z.index),
        colorscale=[[0, "#0E1726"], [0.4, "#1E4A7A"], [0.75, "#2C6BB5"], [1, "#7FC0FA"]],
        text=text.values, texttemplate="%{text}",
        textfont=dict(size=11, color=ui.THEME["ink"]), hovertemplate=hover,
        colorbar=dict(title="% " if view.startswith("Profit") else "₹ lakh",
                      tickfont=dict(color=ui.THEME["muted"]))))
    ui.create_plotly_chart(fig, height=420, legend=False,
                           title=f"{view} by region and category")
    st.caption("Regional margin differences in this dataset mainly reflect each region's category "
               "mix: the Step 10 analysis (BQ16) found no region-category pair more than 2 "
               "percentage points below the national margin for that category.")

with st.expander("Regional table"):
    tbl = reg[["Region", "Revenue", "Profit", "Margin_%", "Orders", "Customers", "Quantity",
               "AOV", "Revenue_Share_%"]]
    st.dataframe(tbl, use_container_width=True, hide_index=True,
                 column_config={
                     "Revenue": st.column_config.NumberColumn(format="₹%.0f"),
                     "Profit": st.column_config.NumberColumn(format="₹%.0f"),
                     "AOV": st.column_config.NumberColumn(format="₹%.0f"),
                     "Margin_%": st.column_config.NumberColumn("Margin %", format="%.2f"),
                     "Revenue_Share_%": st.column_config.NumberColumn("Share %", format="%.2f")})
    ui.download_button(tbl, "regional_performance.csv", key="reg_dl")
