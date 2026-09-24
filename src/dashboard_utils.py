"""STEP 12 - shared UI helpers for the Streamlit application.

Everything the pages have in common lives here: the theme, the KPI card, the
Plotly styling, the number formatters, the filter panel and the small guards
that keep a missing file from turning into a stack trace on screen.

Nothing in this module computes a business number. Values always arrive from
src/data_loader.py, which reads the project's own validated outputs.
"""
from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

import config

CSS_FILE = config.PROJECT_ROOT / "assets" / "css" / "style.css"

# Same palette as the Step 11 Power BI theme, so both front-ends look like one
# platform. The eight categorical hues were validated against the panel surface
# for lightness, chroma, colour-vision separation and contrast.
THEME = {
    "page": "#0B111C", "panel": "#141C2B", "border": "#25324A", "grid": "#223047",
    "ink": "#E6EDF7", "ink_strong": "#FFFFFF", "muted": "#8E9BB3",
    "cat": ["#3987E5", "#D95926", "#199E70", "#C98500", "#D55181", "#008300", "#9085E9", "#E66767"],
    "good": "#0CA30C", "warning": "#FAB219", "serious": "#EC835A", "critical": "#D03B3B",
}
# Fixed meanings, used on every page that shows them
SERIES = {"historical": THEME["cat"][0], "predicted": THEME["cat"][1],
          "forecast": THEME["cat"][2], "baseline": THEME["cat"][3]}

PLOTLY_TEMPLATE = "cri_dark"


def _register_template() -> None:
    if PLOTLY_TEMPLATE in pio.templates:
        return
    t = go.layout.Template()
    t.layout = go.Layout(
        colorway=THEME["cat"],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color=THEME["ink"]),
        title=dict(font=dict(size=15, color=THEME["ink_strong"]), x=0.01, xanchor="left"),
        xaxis=dict(gridcolor=THEME["grid"], zerolinecolor=THEME["grid"], linecolor=THEME["grid"],
                   tickfont=dict(color=THEME["muted"], size=12),
                   title=dict(font=dict(color=THEME["muted"], size=12))),
        yaxis=dict(gridcolor=THEME["grid"], zerolinecolor=THEME["grid"], linecolor=THEME["grid"],
                   tickfont=dict(color=THEME["muted"], size=12),
                   title=dict(font=dict(color=THEME["muted"], size=12))),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=THEME["border"],
                    font=dict(color=THEME["ink"], size=12),
                    orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0),
        hoverlabel=dict(bgcolor=THEME["panel"], bordercolor=THEME["border"],
                        font=dict(color=THEME["ink"], size=12)),
        margin=dict(l=60, r=24, t=46, b=48),
        colorscale=dict(sequential=[[0, "#0E2038"], [0.5, "#2C6BB5"], [1, "#6FB4F5"]]),
    )
    pio.templates[PLOTLY_TEMPLATE] = t


def apply_custom_css() -> None:
    """Inject the dark theme. Called once per script run, from app.py."""
    _register_template()
    try:
        css = CSS_FILE.read_text()
    except OSError:
        st.warning("Theme file `assets/css/style.css` was not found - the app will use "
                   "Streamlit's default styling.")
        return
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------ formatting
def format_currency(value: float | None, unit: str = "auto", decimals: int = 2) -> str:
    """Indian currency formatting: crore / lakh above the thresholds, else rupees."""
    if value is None or pd.isna(value):
        return "-"
    value = float(value)
    a = abs(value)
    if unit == "cr" or (unit == "auto" and a >= 1e7):
        return f"₹{value / 1e7:,.{decimals}f} Cr"
    if unit == "l" or (unit == "auto" and a >= 1e5):
        return f"₹{value / 1e5:,.{decimals}f} L"
    return f"₹{value:,.0f}"


def format_number(value: float | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "-"
    return f"{float(value):,.{decimals}f}"


def format_percentage(value: float | None, decimals: int = 1, signed: bool = False,
                      already_pct: bool = False) -> str:
    """`value` is a ratio unless already_pct=True."""
    if value is None or pd.isna(value):
        return "-"
    v = float(value) * (1 if already_pct else 100)
    sign = "+" if (signed and v > 0) else ""
    return f"{sign}{v:,.{decimals}f}%"


def format_inr_axis(value: float) -> str:
    """Short axis label."""
    a = abs(value)
    if a >= 1e7:
        return f"₹{value / 1e7:.1f} Cr"
    if a >= 1e5:
        return f"₹{value / 1e5:.1f} L"
    if a >= 1e3:
        return f"₹{value / 1e3:.0f}k"
    return f"₹{value:.0f}"


# ----------------------------------------------------------------- components
def create_kpi_card(title: str, value: str, subtitle: str = "", accent: str | None = None,
                    delta: str | None = None, delta_state: str = "flat") -> None:
    """One KPI tile. `value` is already formatted - this function never does arithmetic."""
    accent = accent or THEME["cat"][0]
    delta_html = (f'<div class="k-delta {html.escape(delta_state)}">{html.escape(delta)}</div>'
                  if delta else "")
    st.markdown(
        f'<div class="cri-kpi" style="--accent:{accent}">'
        f'<div class="k-title">{html.escape(title)}</div>'
        f'<div class="k-value">{html.escape(str(value))}</div>'
        f'{delta_html}'
        f'<div class="k-sub">{html.escape(subtitle)}</div>'
        f'</div>', unsafe_allow_html=True)


def kpi_row(cards: list[dict], per_row: int = 6) -> None:
    """Lay KPI cards out in rows that stay readable when the window narrows."""
    for start in range(0, len(cards), per_row):
        chunk = cards[start:start + per_row]
        for col, card in zip(st.columns(len(chunk), gap="small"), chunk):
            with col:
                create_kpi_card(**card)


def panel(body_html: str) -> None:
    st.markdown(f'<div class="cri-panel">{body_html}</div>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    note_html = f'<span class="s-note">{html.escape(note)}</span>' if note else ""
    st.markdown(f'<div class="cri-section"><span class="s-title">{html.escape(title)}</span>'
                f'{note_html}</div>', unsafe_allow_html=True)


def caption(text: str) -> None:
    st.markdown(f'<div class="cri-panel" style="padding:0.6rem 0.9rem">'
                f'<span class="note">{html.escape(text)}</span></div>', unsafe_allow_html=True)


def page_header(title: str, subtitle: str, icon: str = "") -> None:
    st.markdown(f"## {icon} {title}")
    st.markdown(f'<p style="color:{THEME["muted"]};margin-top:-0.6rem;font-size:0.9rem">'
                f'{html.escape(subtitle)}</p>', unsafe_allow_html=True)


def create_plotly_chart(fig: go.Figure, height: int = 380, title: str | None = None,
                        y_title: str | None = None, x_title: str | None = None,
                        legend: bool = True, currency_axis: str | None = None) -> None:
    """Apply the house style and render.

    The chart title is rendered as HTML above the figure rather than inside it: a
    Plotly title and a horizontal legend compete for the same strip of pixels, and
    at dashboard heights the legend wins. `currency_axis` is 'y', 'x' or None.
    """
    if title:
        st.markdown(f'<div class="cri-chart-title">{html.escape(title)}</div>',
                    unsafe_allow_html=True)
    fig.update_layout(template=PLOTLY_TEMPLATE, height=height, title=None,
                      showlegend=legend, hovermode="x unified" if legend else "closest",
                      margin=dict(l=60, r=24, t=46 if legend else 18, b=48))
    # Explicit axis styling: a template alone does not always win against a figure
    # built trace-by-trace, and a bright default gridline ruins a dark theme.
    fig.update_xaxes(gridcolor=THEME["grid"], zerolinecolor=THEME["grid"],
                     linecolor=THEME["grid"], tickfont=dict(color=THEME["muted"], size=12))
    fig.update_yaxes(gridcolor=THEME["grid"], zerolinecolor=THEME["grid"],
                     linecolor=THEME["grid"], tickfont=dict(color=THEME["muted"], size=12))
    if y_title is not None:
        fig.update_yaxes(title_text=y_title, title_font=dict(color=THEME["muted"], size=12))
    if x_title is not None:
        fig.update_xaxes(title_text=x_title, title_font=dict(color=THEME["muted"], size=12))
    if currency_axis == "y":
        fig.update_yaxes(tickprefix="₹", tickformat="~s")
    elif currency_axis == "x":
        fig.update_xaxes(tickprefix="₹", tickformat="~s")
    st.plotly_chart(fig, use_container_width=True, config={
        "displaylogo": False,
        "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d"],
        "toImageButtonOptions": {"format": "png", "scale": 2},
    })


def download_button(df: pd.DataFrame, filename: str, label: str = "Download CSV",
                    key: str | None = None) -> None:
    if df is None or df.empty:
        st.caption("Nothing to download for the current selection.")
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=filename,
                       mime="text/csv", key=key)


# ------------------------------------------------------------------- guards
def validate_dataframe(df: pd.DataFrame | None, required: list[str] | None = None,
                       name: str = "dataset", quiet: bool = False) -> bool:
    """True when `df` is usable. Otherwise show a plain-language message and return False."""
    if df is None:
        if not quiet:
            st.error(f"**{name} is unavailable.** The file it comes from was not found. "
                     f"Re-run the pipeline step that produces it, then reload this page.")
        return False
    if not isinstance(df, pd.DataFrame) or df.empty:
        if not quiet:
            st.warning(f"**{name} is empty.** There are no rows to show - if a filter is "
                       f"applied, widen it.")
        return False
    missing = [c for c in (required or []) if c not in df.columns]
    if missing:
        if not quiet:
            st.error(f"**{name} is missing the column(s):** {', '.join(missing)}. "
                     f"This page needs them, so it cannot be drawn. The file may be from an "
                     f"older pipeline run - re-run the step that produces it.")
        return False
    return True


def guard(fn):
    """Decorator: a page that raises shows a message instead of a stack trace."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:                                  # noqa: BLE001
            st.error("**This section could not be rendered.** The rest of the app is unaffected.")
            with st.expander("Technical detail (for the developer)"):
                st.code(f"{type(exc).__name__}: {exc}")
            return None
    wrapper.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapper


# -------------------------------------------------------------------- filters
def sales_filters(df: pd.DataFrame, key: str, fields: tuple[str, ...] =
                  ("date", "region", "category", "sub_category", "segment")) -> pd.DataFrame:
    """Filter panel for a sales dataframe.

    State is keyed per page (`key`), so one page's filters never move another's.
    Returns the filtered frame; the caller recomputes every number from it.
    """
    with st.expander("Filters", expanded=False):
        cols = st.columns(len(fields), gap="small")
        out = df
        for col, field in zip(cols, fields):
            with col:
                if field == "date" and "Order_Date" in df.columns:
                    dates = pd.to_datetime(df["Order_Date"])
                    lo, hi = dates.min().date(), dates.max().date()
                    picked = st.date_input("Date range", value=(lo, hi), min_value=lo,
                                           max_value=hi, key=f"{key}_date")
                    if isinstance(picked, (tuple, list)) and len(picked) == 2:
                        mask = (dates.dt.date >= picked[0]) & (dates.dt.date <= picked[1])
                        out = out[mask.values]
                elif field in ("region", "category", "sub_category", "segment", "cluster"):
                    colname = {"region": "Region", "category": "Category",
                               "sub_category": "Sub_Category", "segment": "RFM_Segment",
                               "cluster": "Cluster_Label"}[field]
                    if colname not in df.columns:
                        continue
                    options = sorted(x for x in df[colname].dropna().unique())
                    label = colname.replace("_", " ")
                    picked = st.multiselect(label, options, default=[], key=f"{key}_{field}",
                                            placeholder="All")
                    if picked:
                        out = out[out[colname].isin(picked)]
        n_all, n_now = len(df), len(out)
        if n_now < n_all:
            st.caption(f"Showing {n_now:,} of {n_all:,} order lines "
                       f"({n_now / n_all:.1%}) after filtering.")
        else:
            st.caption(f"No filters applied - all {n_all:,} order lines.")
    return out


def active_filter_note(filtered: pd.DataFrame, full: pd.DataFrame) -> None:
    """A visible reminder when a page is showing a subset."""
    if len(filtered) < len(full):
        st.info(f"Filtered view: {len(filtered):,} of {len(full):,} order lines. "
                f"Every figure on this page reflects the filter.")


# ------------------------------------------------------------------ chrome
def app_header(status_ok: bool, status_note: str, meta_lines: list[str]) -> None:
    cls, dot_text = ("cri-status", "ANALYTICS ENGINE ONLINE") if status_ok else \
                    ("cri-status warn", "ANALYTICS ENGINE - LIMITED")
    meta = "<br>".join(html.escape(m) for m in meta_lines)
    st.markdown(
        f'<div class="cri-header">'
        f'  <div>'
        f'    <div class="eyebrow">Customer Revenue Intelligence Platform</div>'
        f'    <div class="title">CUSTOMER REVENUE INTELLIGENCE</div>'
        f'    <div class="subtitle">Transforming Customer Data into Actionable '
        f'Business Intelligence</div>'
        f'    <div style="margin-top:0.7rem"><span class="{cls}"><span class="dot"></span>'
        f'{dot_text}</span> <span style="color:{THEME["muted"]};font-size:0.75rem;'
        f'margin-left:0.5rem">{html.escape(status_note)}</span></div>'
        f'  </div>'
        f'  <div class="meta">{meta}</div>'
        f'</div>', unsafe_allow_html=True)


def app_footer() -> None:
    st.markdown(
        '<div class="cri-footer">'
        '<div><strong>Customer Revenue Intelligence</strong> · '
        'MBA Data Science Internship Project</div>'
        '<div>Synthetic dataset - generated for this project. Not real customer data.</div>'
        '</div>', unsafe_allow_html=True)
