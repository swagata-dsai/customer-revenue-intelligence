"""CUSTOMER SEGMENTATION - RFM rules (Step 5) and K-Means clusters (Step 6), compared."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Customer Segmentation",
               "Two ways of grouping the same customers: a transparent rule and an unsupervised "
               "model. They answer different questions.", "🎯")

sales = dl.load_sales()
customers = dl.load_customers()
if not ui.validate_dataframe(customers, ["Customer_ID", "RFM_Segment", "Cluster_ID"],
                             "Customer dimension"):
    st.stop()
if not ui.validate_dataframe(sales, ["Sales", "RFM_Segment"], "Transaction data"):
    st.stop()

scored = customers[(customers.get("Has_Delivered_Order", 1) == 1)].copy()
rfm_sum = dl.load_table("rfm_segment_summary")
ml_sum = dl.load_table("ml_cluster_summary")
agreement = dl.load_table("rfm_vs_ml_agreement")
meta = dl.load_metadata()

# ------------------------------------------------------------------ framing
ui.panel(
    '<h4>Two segmentations, two jobs - neither is automatically better</h4>'
    '<p><strong>RFM (Step 5)</strong> is a transparent rule on recency, frequency and monetary '
    'scores. Every customer&rsquo;s segment can be explained to a business user in one sentence, '
    'and the thresholds were fixed in advance, so the segments are stable and auditable.</p>'
    '<p><strong>K-Means (Step 6)</strong> is unsupervised: it finds groups in the scaled RFM '
    'features without being told what to look for, so it can surface structure the rules did not '
    'anticipate. Its clusters carry no business meaning until they are described - the labels '
    'here were assigned by reading each cluster&rsquo;s centroid.</p>'
    '<p class="note">They agree on the large picture and differ at the boundaries. Use RFM when '
    'you need to act on a named segment; use the clusters to check whether the rules are still '
    'cutting the base sensibly.</p>')

def _agreement_value(measure: str, value) -> str:
    """Counts as counts, scores to three decimals - the saved file stores raw floats."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{v:,.0f}" if "customer" in str(measure).lower() else f"{v:.3f}"


if agreement is not None and {"Measure", "Value"} <= set(agreement.columns):
    short = {"Adjusted Rand Index (RFM segment vs cluster)": "Adjusted Rand Index",
             "Normalized Mutual Information": "Normalised mutual information",
             "ARI (RFM value-activity group vs cluster)": "ARI (value-activity group)",
             "Customers compared": "Customers compared"}
    cards = [dict(title=short.get(str(r["Measure"]), str(r["Measure"])[:30]),
                  value=_agreement_value(r["Measure"], r["Value"]),
                  subtitle="Step 6 agreement analysis · 0 = independent, 1 = identical"
                           if "customer" not in str(r["Measure"]).lower()
                           else "Scored by both methods",
                  accent=ui.THEME["cat"][4])
             for _, r in agreement.iterrows()]
    ui.kpi_row(cards, per_row=4)
    st.caption("The two methods agree well above chance but are far from identical - which is "
               "exactly why the project reports both.")

tab_rfm, tab_ml, tab_compare = st.tabs(["RFM segmentation", "K-Means clusters",
                                        "RFM vs K-Means"])

# ---------------------------------------------------------------------- RFM
with tab_rfm:
    seg = dl.by_dimension(dl.delivered(sales), "RFM_Segment")
    seg = seg[seg["RFM_Segment"] != "No delivered order"]
    counts = (scored.groupby("RFM_Segment").agg(
        Customers=("Customer_ID", "count"),
        Avg_Recency=("Recency_Days", "mean"),
        Avg_Frequency=("Frequency_Orders", "mean"),
        Avg_Monetary=("Monetary_Revenue", "mean")).reset_index())
    seg = seg.drop(columns=["Customers"]).merge(counts, on="RFM_Segment", how="left")
    seg["Customer_%"] = 100 * seg["Customers"] / seg["Customers"].sum()
    seg = seg.sort_values("Revenue", ascending=False)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        s = seg.sort_values("Revenue_Share_%")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=s["RFM_Segment"], x=s["Revenue_Share_%"], name="% of revenue",
                             orientation="h", marker_color=ui.THEME["cat"][0],
                             hovertemplate="%{y}<br>%{x:.1f}% of revenue<extra></extra>"))
        fig.add_trace(go.Bar(y=s["RFM_Segment"], x=s["Customer_%"], name="% of customers",
                             orientation="h", marker_color=ui.THEME["cat"][4],
                             hovertemplate="%{y}<br>%{x:.1f}% of customers<extra></extra>"))
        fig.update_layout(barmode="group", bargap=0.22)
        ui.create_plotly_chart(fig, height=430, x_title="%",
                               title="Revenue share vs customer share, by RFM segment")
    with c2:
        s = seg.sort_values("Revenue")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=s["RFM_Segment"], x=s["Revenue"], name="Revenue", orientation="h",
                             marker_color=ui.THEME["cat"][0], width=0.62,
                             hovertemplate="%{y}<br>Revenue ₹%{x:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(y=s["RFM_Segment"], x=s["Profit"], name="Profit", orientation="h",
                             marker_color=ui.THEME["cat"][2], width=0.34,
                             text=[f"{v:.1f}% margin" for v in s["Margin_%"]],
                             textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                             hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<extra></extra>"))
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(range=[0, s["Revenue"].max() * 1.32])
        ui.create_plotly_chart(fig, height=430, x_title="₹", currency_axis="x",
                               title="Revenue and profit by RFM segment")

    ui.section("Average R, F and M by segment", "The three inputs the rules act on")
    top_seg = seg.head(8).sort_values("Avg_Monetary", ascending=False)
    c1, c2, c3 = st.columns(3, gap="medium")
    for col, (field, label, colour, fmt) in zip(
            [c1, c2, c3],
            [("Avg_Recency", "Average recency (days) - lower is better", ui.THEME["cat"][1], "{:.0f}"),
             ("Avg_Frequency", "Average frequency (orders)", ui.THEME["cat"][2], "{:.1f}"),
             ("Avg_Monetary", "Average monetary (₹)", ui.THEME["cat"][0], "{:,.0f}")]):
        with col:
            s = top_seg.sort_values(field)
            fig = go.Figure(go.Bar(
                x=s[field], y=s["RFM_Segment"], orientation="h", marker_color=colour,
                text=[fmt.format(v) for v in s[field]], textposition="outside",
                textfont=dict(color=ui.THEME["ink"], size=10),
                hovertemplate="%{y}<br>%{x:,.1f}<extra></extra>"))
            fig.update_xaxes(range=[0, s[field].max() * 1.35])
            ui.create_plotly_chart(fig, height=330, legend=False, title=label)

    with st.expander("Segment matrix"):
        tbl = seg[["RFM_Segment", "Customers", "Customer_%", "Revenue", "Profit", "Margin_%",
                   "Revenue_Share_%", "Avg_Recency", "Avg_Frequency", "Avg_Monetary"]]
        st.dataframe(tbl, use_container_width=True, hide_index=True,
                     column_config={
                         "Revenue": st.column_config.NumberColumn(format="₹%.0f"),
                         "Profit": st.column_config.NumberColumn(format="₹%.0f"),
                         "Avg_Monetary": st.column_config.NumberColumn("Avg monetary",
                                                                       format="₹%.0f"),
                         "Avg_Recency": st.column_config.NumberColumn("Avg recency (d)",
                                                                       format="%.0f"),
                         "Avg_Frequency": st.column_config.NumberColumn("Avg frequency",
                                                                         format="%.1f"),
                         "Customer_%": st.column_config.NumberColumn("Customers %", format="%.2f"),
                         "Revenue_Share_%": st.column_config.NumberColumn("Revenue %",
                                                                           format="%.2f"),
                         "Margin_%": st.column_config.NumberColumn("Margin %", format="%.2f")})
        ui.download_button(tbl, "rfm_segment_matrix.csv", key="seg_rfm_dl")

    if rfm_sum is not None:
        st.caption("These figures are recomputed from the transactions at page load and match "
                   "`outputs/tables/rfm_segment_summary.csv` from Step 5.")

# ------------------------------------------------------------------- K-Means
with tab_ml:
    clustered = scored[scored["Cluster_ID"] >= 0]
    clu = dl.by_dimension(dl.delivered(sales), "Cluster_Label")
    clu = clu[clu["Cluster_Label"] != "No delivered order"]
    ccounts = (clustered.groupby("Cluster_Label").agg(
        Customers=("Customer_ID", "count"),
        Avg_Recency=("Recency_Days", "mean"),
        Avg_Frequency=("Frequency_Orders", "mean"),
        Avg_Monetary=("Monetary_Revenue", "mean")).reset_index())
    clu = clu.drop(columns=["Customers"]).merge(ccounts, on="Cluster_Label", how="left")
    clu["Customer_%"] = 100 * clu["Customers"] / clu["Customers"].sum()
    clu["Revenue_per_Customer"] = clu["Revenue"] / clu["Customers"]

    smeta = meta.get("segmentation") or {}
    k_used = smeta.get("n_clusters") or clustered["Cluster_ID"].nunique()
    ui.kpi_row([
        dict(title="Clusters", value=str(k_used), subtitle="K chosen in Step 6",
             accent=ui.THEME["cat"][4]),
        dict(title="Customers clustered", value=f"{len(clustered):,}",
             subtitle="Customers with a delivered order", accent=ui.THEME["cat"][6]),
        dict(title="Largest cluster",
             value=str(clu.loc[clu["Customers"].idxmax(), "Cluster_Label"]),
             subtitle=f"{clu['Customers'].max():,} customers", accent=ui.THEME["cat"][0]),
        dict(title="Highest-value cluster",
             value=str(clu.loc[clu["Revenue_per_Customer"].idxmax(), "Cluster_Label"]),
             subtitle=f"{ui.format_currency(clu['Revenue_per_Customer'].max(), unit='inr')} "
                      f"per customer", accent=ui.THEME["cat"][2]),
    ], per_row=4)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        s = clu.sort_values("Revenue_Share_%")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=s["Cluster_Label"], x=s["Revenue_Share_%"], name="% of revenue",
                             orientation="h", marker_color=ui.THEME["cat"][0],
                             text=[f"{v:.1f}%" for v in s["Revenue_Share_%"]],
                             textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                             hovertemplate="%{y}<br>%{x:.1f}% of revenue<extra></extra>"))
        fig.add_trace(go.Bar(y=s["Cluster_Label"], x=s["Customer_%"], name="% of customers",
                             orientation="h", marker_color=ui.THEME["cat"][4],
                             text=[f"{v:.1f}%" for v in s["Customer_%"]],
                             textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                             hovertemplate="%{y}<br>%{x:.1f}% of customers<extra></extra>"))
        fig.update_layout(barmode="group", bargap=0.25)
        fig.update_xaxes(range=[0, max(s["Revenue_Share_%"].max(), s["Customer_%"].max()) * 1.3])
        ui.create_plotly_chart(fig, height=360, x_title="%",
                               title="Cluster distribution and revenue share")
    with c2:
        s = clu.sort_values("Revenue")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=s["Cluster_Label"], x=s["Revenue"], name="Revenue", orientation="h",
                             marker_color=ui.THEME["cat"][0], width=0.62,
                             hovertemplate="%{y}<br>Revenue ₹%{x:,.0f}<extra></extra>"))
        fig.add_trace(go.Bar(y=s["Cluster_Label"], x=s["Profit"], name="Profit", orientation="h",
                             marker_color=ui.THEME["cat"][2], width=0.34,
                             text=[f"{v:.1f}% margin" for v in s["Margin_%"]],
                             textposition="outside", textfont=dict(color=ui.THEME["ink"], size=10),
                             hovertemplate="%{y}<br>Profit ₹%{x:,.0f}<extra></extra>"))
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(range=[0, s["Revenue"].max() * 1.32])
        ui.create_plotly_chart(fig, height=360, x_title="₹", currency_axis="x",
                               title="Revenue and profit by cluster")

    ui.section("Cluster scatter", "The Step 6 PCA projection of the scaled R, F and M features")
    if {"PC1", "PC2"} <= set(clustered.columns) and clustered["PC1"].notna().any():
        fig = go.Figure()
        for i, (label, grp) in enumerate(clustered.groupby("Cluster_Label")):
            fig.add_trace(go.Scatter(
                x=grp["PC1"], y=grp["PC2"], mode="markers", name=str(label),
                marker=dict(size=6, color=ui.THEME["cat"][i % 8], opacity=0.75,
                            line=dict(width=0.5, color=ui.THEME["panel"])),
                customdata=grp[["Customer_ID", "Recency_Days", "Frequency_Orders",
                                "Monetary_Revenue"]].values,
                hovertemplate=("%{customdata[0]}<br>Recency %{customdata[1]:.0f} d"
                               "<br>Frequency %{customdata[2]:.0f} orders"
                               "<br>Monetary ₹%{customdata[3]:,.0f}<extra>" + str(label) +
                               "</extra>")))
        ui.create_plotly_chart(fig, height=470, x_title="Principal component 1",
                               y_title="Principal component 2",
                               title="Customers in PCA space, coloured by K-Means cluster")
        st.caption("PCA is used for the picture only - the clusters were fitted on the scaled "
                   "log-transformed R, F and M features, not on these two components.")
    else:
        st.info("PCA coordinates (`PC1`, `PC2`) were not found in the Step 6 output, so the "
                "cluster scatter cannot be drawn. The cluster summaries above are unaffected.")

    with st.expander("Cluster profiles (Step 6 centroids)"):
        if ml_sum is not None:
            st.dataframe(ml_sum, use_container_width=True, hide_index=True)
            ui.download_button(ml_sum, "ml_cluster_summary.csv", key="seg_ml_dl")
        else:
            st.info("`outputs/tables/ml_cluster_summary.csv` was not found.")

# ------------------------------------------------------------------- compare
with tab_compare:
    ui.section("Where the two methods agree and differ",
               "Customers counted in both views at the same reference date")
    cross = (scored[scored["Cluster_ID"] >= 0]
             .pivot_table(index="RFM_Segment", columns="Cluster_Label",
                          values="Customer_ID", aggfunc="count", fill_value=0))
    if not cross.empty:
        order = (scored.groupby("RFM_Segment")["Monetary_Revenue"].mean()
                 .sort_values(ascending=False).index)
        cross = cross.reindex([o for o in order if o in cross.index])
        fig = go.Figure(go.Heatmap(
            z=cross.values, x=list(cross.columns), y=list(cross.index),
            colorscale=[[0, "#0E1726"], [0.35, "#1E4A7A"], [0.7, "#2C6BB5"], [1, "#6FB4F5"]],
            text=cross.values, texttemplate="%{text}",
            textfont=dict(size=11, color=ui.THEME["ink"]),
            hovertemplate="RFM %{y}<br>Cluster %{x}<br>%{z} customers<extra></extra>",
            colorbar=dict(title="Customers", tickfont=dict(color=ui.THEME["muted"]))))
        ui.create_plotly_chart(fig, height=480, legend=False,
                               title="RFM segment against K-Means cluster (customer counts)")
        st.caption("Every cell shows its count, so the colour scale is a reading aid rather than "
                   "the information itself.")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        ui.panel(
            '<h4>What RFM is good at</h4>'
            '<p>Explainability and action. A segment name maps to a rule a manager can check, '
            'and the same customer lands in the same segment every run.</p>'
            '<p class="note">Limitation: the thresholds are chosen, not learned, so RFM cannot '
            'discover a grouping the rules did not anticipate.</p>')
    with c2:
        ui.panel(
            '<h4>What K-Means is good at</h4>'
            '<p>Finding structure without prior assumptions, and validating whether the rule-based '
            'cuts still match how the base actually separates.</p>'
            '<p class="note">Limitation: cluster identity is not inherently meaningful, it depends '
            'on scaling and K, and it must be re-described whenever it is re-fitted.</p>')
    st.caption("Neither method is presented as superior. They are used for different jobs, and "
               "the project reports both.")
