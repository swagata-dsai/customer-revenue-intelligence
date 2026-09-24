"""BUSINESS RECOMMENDATIONS - finding → implication → action, each one traceable."""
from __future__ import annotations

import streamlit as st

from src import dashboard_utils as ui
from src import data_loader as dl

ui.page_header("Business Recommendations",
               "Each card states the finding it rests on, what that implies, and the action it "
               "suggests - with the analysis it came from.", "💡")

recs = dl.load_recommendations()
if recs is None:
    st.error("**`powerbi/data/Recommendations.csv` was not found.** These recommendations are "
             "generated from the Step 4-10 output tables by `src/powerbi_prep.py`; this page "
             "shows them rather than writing new ones, so that every claim stays traceable. "
             "Run `python -c \"from src.powerbi_prep import run_powerbi_prep; run_powerbi_prep()\"` "
             "to regenerate the file.")
    st.stop()

required = ["Area", "Recommendation", "Evidence", "Suggested_Action", "Supporting_Metric",
            "Metric_Value", "Analytical_Source"]
if not ui.validate_dataframe(recs, required, "Recommendations"):
    st.stop()

AREA_META = {
    "Customer": ("👥 Customer Strategy", ui.THEME["cat"][0]),
    "Product": ("📦 Product Strategy", ui.THEME["cat"][3]),
    "Regional": ("🌍 Regional Strategy", ui.THEME["cat"][2]),
    "Revenue": ("💰 Revenue Strategy", ui.THEME["cat"][6]),
    "Forecasting & Planning": ("📈 Forecast & Planning", ui.THEME["cat"][4]),
}

ui.panel(
    f'<h4>How to read this page</h4>'
    f'<p>Every recommendation was computed from a named project output by '
    f'<code>src/powerbi_prep.py</code>, not written by hand: the <strong>finding</strong> is the '
    f'measured result, the <strong>implication</strong> is the recommendation it leads to, and '
    f'the <strong>action</strong> is what to do about it. The source query, table or model file '
    f'is printed on every card so any figure can be checked.</p>'
    f'<p class="note">{len(recs)} recommendations across {recs["Area"].nunique()} areas. The '
    f'data is synthetic, so the actions are demonstrations of method rather than advice about a '
    f'real market.</p>')

# ------------------------------------------------------------------- filters
c1, c2 = st.columns([2, 1], gap="medium")
with c1:
    areas = st.multiselect("Show areas", list(AREA_META.keys()),
                           default=list(AREA_META.keys()), key="rec_areas",
                           format_func=lambda a: AREA_META[a][0])
with c2:
    search = st.text_input("Search the recommendations", "", key="rec_search",
                           placeholder="e.g. discount, retention, forecast")

view = recs[recs["Area"].isin(areas)] if areas else recs
if search:
    mask = view.apply(lambda r: search.lower() in " ".join(str(v) for v in r.values).lower(),
                      axis=1)
    view = view[mask]

if view.empty:
    st.warning("No recommendations match the current selection.")
    st.stop()

sort_col = "Recommendation_ID" if "Recommendation_ID" in view.columns else "Area"
order_cols = ([c for c in ["Area_Order", sort_col] if c in view.columns] or [sort_col])
view = view.sort_values(order_cols)

st.caption(f"Showing {len(view)} of {len(recs)} recommendations.")

# --------------------------------------------------------------------- cards
for area in [a for a in AREA_META if a in view["Area"].unique()]:
    label, colour = AREA_META[area]
    group = view[view["Area"] == area]
    ui.section(label, f"{len(group)} recommendation{'s' if len(group) != 1 else ''}")
    for _, r in group.iterrows():
        rec_id = r.get("Recommendation_ID", "")
        st.markdown(
            f'<div class="cri-rec" style="--accent:{colour}">'
            f'  <div class="r-head">Recommendation {rec_id} · {area}</div>'
            f'  <div class="r-label">Finding</div>'
            f'  <div class="r-body">{r["Evidence"]}</div>'
            f'  <div class="r-label">Implication</div>'
            f'  <div class="r-body">{r["Recommendation"]}</div>'
            f'  <div class="r-label">Action</div>'
            f'  <div class="r-body">{r["Suggested_Action"]}</div>'
            f'  <div class="r-src"><strong>{r["Supporting_Metric"]}:</strong> '
            f'{r["Metric_Value"]} &nbsp;·&nbsp; Source: {r["Analytical_Source"]}</div>'
            f'</div>', unsafe_allow_html=True)

# --------------------------------------------------------------------- table
with st.expander("All recommendations as a table"):
    cols = [c for c in ["Recommendation_ID", "Area", "Recommendation", "Evidence",
                        "Suggested_Action", "Supporting_Metric", "Metric_Value",
                        "Analytical_Source"] if c in view.columns]
    st.dataframe(view[cols], use_container_width=True, hide_index=True)
    ui.download_button(view[cols], "business_recommendations.csv", key="rec_dl")

st.caption("No recommendation on this page was invented for the dashboard: each one names the "
           "saved query, table or model metadata that produced its figure.")
