"""Customer Revenue Intelligence - Streamlit application (STEP 12).

Run from the project root:

    streamlit run app.py

The entry point does four things and nothing else: set the page config, inject the
theme, draw the header and footer, and route to a page module in `pages/`. All the
data work lives in `src/data_loader.py`, all the shared UI in `src/dashboard_utils.py`.

SYNTHETIC DATA. Every figure comes from the project's own validated outputs
(Steps 3-11); nothing in this application is invented or hard-coded.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import data_loader as dl            # noqa: E402
from src import dashboard_utils as ui        # noqa: E402

st.set_page_config(
    page_title="Customer Revenue Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Customer Revenue Intelligence · MBA Data Science Internship Project. "
                         "Synthetic dataset."},
)

ui.apply_custom_css()

# --------------------------------------------------------------------- status
# The indicator reflects what actually loaded on this run - it is never decorative.
status = dl.data_status()
sales = dl.load_sales()

if status["ok"] and sales is not None:
    k = dl.kpis(sales)
    period = f"{sales['Order_Date'].min():%b %Y} - {sales['Order_Date'].max():%b %Y}"
    meta = [
        f"{len(sales):,} order lines · {k['customers']:,} customers",
        f"Period {period} · reference date {dl.REFERENCE_DATE}",
        f"{status['models_loaded']} of {status['models_total']} models loaded",
    ]
    note = "Database connected" if status["database"] else "Reading processed files"
else:
    meta = ["Some project outputs could not be read",
            "Pages that need them will say so",
            f"{status['models_loaded']} of {status['models_total']} models loaded"]
    note = "Limited data available"

ui.app_header(status_ok=bool(status["ok"]), status_note=note, meta_lines=meta)

if not status["ok"]:
    st.error(
        "**Some project outputs are missing.** The application is running, but any page that "
        "needs a missing file will explain what is unavailable instead of showing a number. "
        "Re-run the pipeline steps (see the README) to restore full functionality."
    )

# ----------------------------------------------------------------- navigation
PAGES = {
    "Overview": [
        st.Page("pages/home.py", title="HOME", icon="🏠", default=True),
        st.Page("pages/executive.py", title="EXECUTIVE OVERVIEW", icon="📊"),
    ],
    "Analytics": [
        st.Page("pages/revenue.py", title="REVENUE INTELLIGENCE", icon="💰"),
        st.Page("pages/customers.py", title="CUSTOMER INTELLIGENCE", icon="👥"),
        st.Page("pages/segmentation.py", title="CUSTOMER SEGMENTATION", icon="🎯"),
        st.Page("pages/products.py", title="PRODUCT ANALYTICS", icon="📦"),
        st.Page("pages/regional.py", title="REGIONAL ANALYTICS", icon="🌍"),
    ],
    "Models": [
        st.Page("pages/prediction.py", title="REVENUE PREDICTION", icon="🔮"),
        st.Page("pages/forecasting.py", title="SALES FORECAST", icon="📈"),
    ],
    "Decisions & data": [
        st.Page("pages/recommendations.py", title="BUSINESS RECOMMENDATIONS", icon="💡"),
        st.Page("pages/data_explorer.py", title="DATA EXPLORER", icon="📂"),
        st.Page("pages/about.py", title="ABOUT PROJECT", icon="ℹ️"),
    ],
}

with st.sidebar:
    st.markdown(
        '<div class="cri-side-brand">'
        '<div class="b-mark">◆ CRI PLATFORM</div>'
        '<div class="b-name">Customer Revenue<br>Intelligence</div>'
        '</div>', unsafe_allow_html=True)

page = st.navigation(PAGES, position="sidebar")

with st.sidebar:
    st.markdown("---")
    st.markdown(
        f'<div class="cri-side-note">'
        f'<strong style="color:{ui.THEME["ink"]}">Data</strong><br>'
        f'Synthetic dataset, generated for this project.<br>'
        f'Revenue = Delivered order lines only.<br>'
        f'Customer snapshot: {dl.REFERENCE_DATE}.'
        f'</div>', unsafe_allow_html=True)
    if st.button("Clear cache & reload", use_container_width=True,
                 help="Re-reads every file from disk. Use after re-running a pipeline step."):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

page.run()

ui.app_footer()
