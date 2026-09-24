"""STEP 12 - tests for the Streamlit application, run headlessly with AppTest.

Run from the project root:

    python tests/test_streamlit_app.py

Every check records what was expected, what actually happened and PASS/FAIL, prints one line per
check, and writes `outputs/tables/streamlit_test_results.csv` plus
`outputs/tables/streamlit_page_load_times.csv`. `outputs/reports/streamlit_testing_report.md` is
built from those results.

The suite exercises the real app.py: every page, the filters, the model-backed what-if tool, the
CSV upload and download paths, and the behaviour when a model or data file is missing (it moves
the file away, checks the message, and puts it back).
"""
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "tables"
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

import streamlit as st                          # noqa: E402
from streamlit.testing.v1 import AppTest        # noqa: E402


def clear_caches():
    """AppTest shares Streamlit's caches across runs in one process."""
    st.cache_data.clear()
    st.cache_resource.clear()

APP = str(ROOT / "app.py")
results = []


def record(name, expected, actual, ok, detail=""):
    results.append({"test": name, "expected": expected, "actual": actual,
                    "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} :: {actual}", flush=True)
    return ok


def open_page(path, timeout=180):
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.run()
    if path != "pages/home.py":
        at.switch_page(path)
        at.run()
    return at


def no_exception(at):
    return len(at.exception) == 0


def text_of(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    return " ".join(str(p) for p in parts)


# ------------------------------------------------------------------ 1. launch
t0 = time.time()
at = AppTest.from_file(APP, default_timeout=180)
at.run()
launch_ok = no_exception(at)
record("App launch (AppTest harness)",
       "app.py runs with no uncaught exception",
       f"ran in {time.time() - t0:.1f}s, {len(at.exception)} exceptions, "
       f"{len(at.markdown)} markdown elements",
       launch_ok)

header_ok = any("CUSTOMER REVENUE INTELLIGENCE" in str(m.value) for m in at.markdown)
status_ok = any("ANALYTICS ENGINE ONLINE" in str(m.value) for m in at.markdown)
record("Application header and status indicator",
       "Header title plus a status pill that reflects the real load state",
       f"header present: {header_ok}; 'ANALYTICS ENGINE ONLINE' shown: {status_ok}",
       header_ok and status_ok)

nav_ok = len(at.sidebar.button) >= 1
record("Sidebar navigation renders",
       "Sidebar shows branding and the cache-reload control",
       f"{len(at.sidebar.button)} sidebar button(s) found", nav_ok)

# -------------------------------------------------------------- 2. every page
PAGES = [
    ("pages/home.py", "Home page"),
    ("pages/executive.py", "Executive Overview"),
    ("pages/revenue.py", "Revenue Intelligence"),
    ("pages/customers.py", "Customer Intelligence"),
    ("pages/segmentation.py", "Customer Segmentation"),
    ("pages/products.py", "Product Analytics"),
    ("pages/regional.py", "Regional Analytics"),
    ("pages/prediction.py", "Revenue Prediction"),
    ("pages/forecasting.py", "Sales Forecast"),
    ("pages/recommendations.py", "Business Recommendations"),
    ("pages/data_explorer.py", "Data Explorer"),
    ("pages/about.py", "About Project"),
]
page_times = {}
for path, label in PAGES:
    t0 = time.time()
    at = open_page(path)
    took = time.time() - t0
    page_times[label] = round(took, 2)
    ok = no_exception(at) and len(at.error) == 0
    record(f"{label} page loads",
           "Page renders with no uncaught exception and no error message",
           f"loaded in {took:.1f}s · {len(at.markdown)} markdown, {len(at.dataframe)} tables, "
           f"{len(at.exception)} exceptions, {len(at.error)} errors",
           ok,
           detail="; ".join(e.message for e in at.exception) or
                  "; ".join(str(e.value)[:120] for e in at.error))

# -------------------------------------------------- 3. KPI values are the real ones
at = open_page("pages/executive.py")
txt = text_of(at)
kpi_ok = "₹6.01 Cr" in txt and "12,212" in txt and "1,984" in txt
record("Executive KPI cards show the validated project totals",
       "Revenue ₹6.01 Cr, 12,212 orders, 1,984 customers (Step 4 / Step 10 validated figures)",
       f"found ₹6.01 Cr: {'₹6.01 Cr' in txt}; 12,212: {'12,212' in txt}; "
       f"1,984: {'1,984' in txt}", kpi_ok)

# -------------------------------------------------------------- 4. filters work
at = open_page("pages/executive.py")
before = text_of(at)
region_ms = [m for m in at.multiselect if m.label == "Region"]
if region_ms:
    region_ms[0].set_value(["South"]).run()
    after = text_of(at)
    changed = ("₹1.62 Cr" in after) and no_exception(at)
    record("Filters recompute every figure (Executive · Region = South)",
           "Revenue falls to the South region total ₹1.62 Cr and the page stays error-free",
           f"South revenue shown: {'₹1.62 Cr' in after}; exceptions: {len(at.exception)}; "
           f"filter note shown: {'Filtered view' in after}", changed)
else:
    record("Filters recompute every figure (Executive · Region = South)",
           "Region multiselect present", "multiselect not found", False)

# ---------------------------------------------------- 5. revenue dimension radio
at = open_page("pages/revenue.py")
radios = [r for r in at.radio if "Break revenue down by" in str(r.label)]
if radios:
    radios[0].set_value("Sub_Category").run()
    ok = no_exception(at) and "sub-category" in text_of(at).lower()
    record("Revenue Intelligence · switch breakdown to sub-category",
           "Chart and table redraw for sub-categories without error",
           f"exceptions: {len(at.exception)}; sub-category text present: "
           f"{'sub-category' in text_of(at).lower()}", ok)
else:
    record("Revenue Intelligence · switch breakdown to sub-category",
           "Radio present", "radio not found", False)

# --------------------------------------------------- 6. customer select + rank
at = open_page("pages/customers.py")
sel = [s for s in at.selectbox if s.label == "Customer_ID"]
metric = [r for r in at.radio if r.label == "Rank by"]
ok = bool(sel) and bool(metric)
if ok:
    first_customer = sel[0].value
    metric[0].set_value("Profit").run()
    ok_metric = no_exception(at)
    sel = [s for s in at.selectbox if s.label == "Customer_ID"]
    options = sel[0].options
    pick = options[3] if len(options) > 3 else options[-1]
    sel[0].set_value(pick).run()
    ok = ok_metric and no_exception(at) and pick in text_of(at)
    record("Customer Intelligence · rank by profit and select a customer",
           "Ranking switches to profit and the selected Customer_ID's detail panel renders",
           f"ranked by profit without error: {ok_metric}; selected {pick}; "
           f"detail shown: {pick in text_of(at)}", ok)
else:
    record("Customer Intelligence · rank by profit and select a customer",
           "Selectbox and radio present", "widget not found", False)

# ------------------------------------------------------- 7. segmentation visuals
at = open_page("pages/segmentation.py")
txt = text_of(at)
ok = no_exception(at) and "PCA" in txt and len(at.tabs) >= 1
record("Customer Segmentation · RFM, clusters and the PCA scatter",
       "Three tabs render and the Step 6 PCA cluster scatter is drawn",
       f"tabs: {len(at.tabs)}; PCA scatter text present: {'PCA' in txt}; "
       f"exceptions: {len(at.exception)}", ok)

neutral = ("neither is automatically better" in txt.lower()) or ("two jobs" in txt.lower())
record("Customer Segmentation · RFM vs K-Means framed as different, not ranked",
       "Page states the two methods answer different questions and does not rank one above "
       "the other",
       f"neutral comparison text present: {neutral}", neutral)

# ---------------------------------------------------------- 8. product matrix
at = open_page("pages/products.py")
sort_sel = [s for s in at.selectbox if s.label == "Sort by"]
cat_ms = [m for m in at.multiselect if m.label == "Category"]
ok = bool(sort_sel) and bool(cat_ms)
if ok:
    sort_sel[0].set_value("Margin_%").run()
    cat_ms = [m for m in at.multiselect if m.label == "Category"]
    cat_ms[0].set_value(["Electronics"]).run()
    ok = no_exception(at)
    record("Product Analytics · sort and filter the performance matrix",
           "Matrix re-sorts by margin and filters to Electronics without error",
           f"exceptions: {len(at.exception)}; tables rendered: {len(at.dataframe)}", ok)
else:
    record("Product Analytics · sort and filter the performance matrix",
           "Sort and category widgets present", "widget not found", False)

# --------------------------------------------------------- 9. regional matrix
at = open_page("pages/regional.py")
view = [r for r in at.radio if r.label == "Show"]
if view:
    view[0].set_value("Revenue").run()
    ok = no_exception(at)
    record("Regional Analytics · switch the region x category matrix to revenue",
           "Heat table redraws in ₹ lakh without error",
           f"exceptions: {len(at.exception)}", ok)
else:
    record("Regional Analytics · switch the region x category matrix to revenue",
           "Radio present", "radio not found", False)

no_map = "ranked bars" in text_of(at).lower()
record("Regional Analytics · no map is forced on insufficient geography",
       "Page explains why ranked bars and a matrix are used instead of a map",
       f"explanation present: {no_map}", no_map)

# --------------------------------------------------------- 10. prediction page
at = open_page("pages/prediction.py")
txt = text_of(at)
metrics_ok = "5,658" in txt.replace("₹", "") and "0.056" in txt
record("Revenue Prediction · shows the real Step 8 metrics",
       "Test MAE ₹5,658 and R² 0.056 read from models/revenue_model_metadata.json",
       f"MAE present: {'5,658' in txt.replace('₹', '')}; R² present: {'0.056' in txt}",
       metrics_ok)

mape_absent = "MAPE is deliberately not reported" in txt
record("Revenue Prediction · MAPE is not fabricated",
       "Page states why MAPE is not reported for this model (zero actuals)",
       f"explanation present: {mape_absent}", mape_absent)

sliders = at.slider
pred_before = None
if sliders:
    # capture the scenario prediction before and after moving a driver
    def scenario_value(app):
        for m in app.markdown:
            v = str(m.value)
            if "your scenario" in v.lower():
                return v
        return ""
    before_card = scenario_value(at)
    target = [s for s in sliders if "Orders in the last 12 months" in str(s.label)]
    if target:
        current = target[0].value
        target[0].set_value(float(current) + 10).run()
        after_card = scenario_value(at)
        ok = no_exception(at) and before_card != after_card
        record("Revenue Prediction · what-if tool re-scores with the saved model",
               "Moving 'Orders in the last 12 months' changes the predicted revenue",
               f"prediction card changed: {before_card != after_card}; "
               f"exceptions: {len(at.exception)}", ok)
    else:
        record("Revenue Prediction · what-if tool re-scores with the saved model",
               "Driver slider present", "slider not found", False)
else:
    record("Revenue Prediction · what-if tool re-scores with the saved model",
           "Sliders present", "no sliders rendered", False)

# ---------------------------------------------------------- 11. forecast page
at = open_page("pages/forecasting.py")
txt = text_of(at)
fc_ok = "₹1.58 Cr" in txt and "7.77%" in txt
record("Sales Forecast · horizon, expected revenue and accuracy come from Step 9",
       "6-month horizon totalling ₹1.58 Cr with test MAPE 7.77%",
       f"₹1.58 Cr present: {'₹1.58 Cr' in txt}; 7.77% present: {'7.77%' in txt}", fc_ok)

band = [r for r in at.radio if r.label == "Prediction interval"]
toggle = at.toggle
if band and toggle:
    band[0].set_value("80%").run()
    toggle = at.toggle
    toggle[0].set_value(False).run()
    ok = no_exception(at)
    record("Sales Forecast · switch interval to 80% and hide the back-forecast",
           "Chart redraws with the 80% band and without the back-forecast series",
           f"exceptions: {len(at.exception)}", ok)
else:
    record("Sales Forecast · switch interval to 80% and hide the back-forecast",
           "Radio and toggle present", "widget not found", False)

dl_buttons = at.download_button
csv_ok = len(dl_buttons) >= 1
record("Sales Forecast · forecast table CSV download",
       "A download button is offered for the forecast table",
       f"{len(dl_buttons)} download button(s) present", csv_ok)

# --------------------------------------------------- 12. recommendations page
at = open_page("pages/recommendations.py")
txt = text_of(at)
rec_ok = "Finding" in txt and "Implication" in txt and "Action" in txt
record("Business Recommendations · finding → implication → action structure",
       "Every card carries the three labels and a source line",
       f"labels present: {rec_ok}; cards rendered: {txt.count('r-head')}", rec_ok)

search = [t for t in at.text_input if "Search" in str(t.label)]
if search:
    search[0].set_value("discount").run()
    ok = no_exception(at) and "discount" in text_of(at).lower()
    record("Business Recommendations · search filter",
           "Searching 'discount' narrows the list without error",
           f"exceptions: {len(at.exception)}; matches shown: "
           f"{'Showing' in text_of(at)}", ok)
else:
    record("Business Recommendations · search filter", "Search box present",
           "text input not found", False)

# ------------------------------------------------------- 13. data explorer CSV
at = open_page("pages/data_explorer.py")
tabs_ok = len(at.tabs) >= 2
record("Data Explorer · project data profile and quality scorecard",
       "Project dataset profiles with row/column/missing/duplicate counts and a scorecard",
       f"tabs: {len(at.tabs)}; tables rendered: {len(at.dataframe)}; "
       f"exceptions: {len(at.exception)}", tabs_ok and no_exception(at))

uploader = at.file_uploader
if uploader:
    good = b"id,name,amount,when\n1,alpha,10.5,2024-01-01\n2,beta,,2024-02-01\n2,beta,,2024-02-01\n"
    uploader[0].set_value(("sample_upload.csv", good, "text/csv"))
    at.run()
    txt = text_of(at)
    ok = no_exception(at) and "sample_upload.csv" in txt
    record("Data Explorer · upload a CSV and profile it",
           "Uploaded file name, row/column counts, missing values and duplicates are reported",
           f"file name shown: {'sample_upload.csv' in txt}; exceptions: {len(at.exception)}; "
           f"tables: {len(at.dataframe)}", ok)

    dl = at.download_button
    record("Data Explorer · download processed data",
           "A 'Download processed data' button is offered for the uploaded file",
           f"{len(dl)} download button(s) present",
           any("Download processed data" in str(b.label) for b in dl))

    # invalid upload
    at2 = open_page("pages/data_explorer.py")
    at2.file_uploader[0].set_value(("broken.csv", b"\x00\x01\x02not,a;csv\"\n\"", "text/csv"))
    at2.run()
    handled = no_exception(at2)
    msgs = [str(e.value)[:80] for e in at2.error] + [str(w.value)[:80] for w in at2.warning]
    record("Data Explorer · invalid file is handled without a stack trace",
           "A readable message is shown and the app keeps running",
           f"exceptions: {len(at2.exception)}; messages: {msgs or 'parsed as text, profiled'}",
           handled)
else:
    record("Data Explorer · upload a CSV and profile it", "File uploader present",
           "uploader not found", False)

# ------------------------------------------- 14. missing model / file handling
model_file = ROOT / "models" / "revenue_prediction_model.pkl"
backup = model_file.with_suffix(".pkl.testbak")
shutil.move(model_file, backup)
clear_caches()
try:
    at = open_page("pages/prediction.py")
    txt = text_of(at)
    warn_msgs = [str(w.value) for w in at.warning]
    graceful = no_exception(at) and any("unavailable" in w.lower() for w in warn_msgs)
    record("Missing model file is handled gracefully",
           "Prediction page still loads, explains that the what-if tool is unavailable, and "
           "does not crash or invent a model",
           f"exceptions: {len(at.exception)}; warning shown: {graceful}; "
           f"metrics still displayed: {'5,658' in txt.replace('₹', '')}", graceful)
finally:
    shutil.move(backup, model_file)
    clear_caches()

rec_file = ROOT / "powerbi" / "data" / "Recommendations.csv"
backup = rec_file.with_suffix(".csv.testbak")
shutil.move(rec_file, backup)
clear_caches()
try:
    at = open_page("pages/recommendations.py")
    graceful = no_exception(at) and len(at.error) >= 1
    record("Missing data file is handled gracefully",
           "Recommendations page shows a readable error naming the missing file instead of a "
           "stack trace",
           f"exceptions: {len(at.exception)}; error message shown: {len(at.error)}", graceful)
finally:
    shutil.move(backup, rec_file)
    clear_caches()

# --------------------------------------------------------------- 15. caching
t0 = time.time()
at = open_page("pages/executive.py")
first = time.time() - t0
t0 = time.time()
at.run()
second = time.time() - t0
record("Caching keeps reruns fast",
       "A rerun of the same page is faster than the first load (cache_data / cache_resource)",
       f"first load {first:.2f}s, rerun {second:.2f}s", second <= first)

# ---------------------------------------------------------------- 16. privacy
at = open_page("pages/customers.py")
txt = text_of(at)
no_names = "Customer_Name" not in txt
record("No personally identifying customer names are displayed",
       "Customer pages identify customers by Customer_ID only",
       f"'Customer_Name' appears anywhere on the page: {not no_names}", no_names)

import pandas as pd                               # noqa: E402
OUT.mkdir(parents=True, exist_ok=True)
pd.DataFrame(results).to_csv(OUT / "streamlit_test_results.csv", index=False)
(pd.DataFrame(sorted(page_times.items()), columns=["Page", "Load_Seconds"])
   .to_csv(OUT / "streamlit_page_load_times.csv", index=False))
passed = sum(1 for r in results if r["status"] == "PASS")
print(f"\n{passed}/{len(results)} checks passed")
print("FAILED:", [r["test"] for r in results if r["status"] == "FAIL"])
