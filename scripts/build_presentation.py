"""
build_presentation.py - Step 15: build the Summer Internship PPT.

The deck is built ON TOP of the university-supplied template
(assets/templates/summer_internship_template.pptx).  The template's design -
layouts, colours, fonts, logos, slide numbering, Thank-You slide - is left
exactly as supplied; only the placeholder text is replaced and project
figures are inserted.

Every number on every slide is read at build time from
outputs/tables/report_facts.json, the same fact pack the written report uses,
so the deck cannot disagree with the report.

Usage
-----
    python scripts/build_presentation.py
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Emu, Pt

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
TEMPLATE = ROOT / "assets" / "templates" / "summer_internship_template.pptx"
FIG = ROOT / "outputs" / "figures"
OUT_DIR = ROOT / "outputs" / "presentation"
WORK = ROOT / "work" / "ppt"
STEM = "Customer_Revenue_Intelligence_Summer_Internship_Presentation"
PPTX = OUT_DIR / f"{STEM}.pptx"
PDF = OUT_DIR / f"{STEM}.pdf"

ADD_SLIDE = Path(
    "/root/.claude/skills/synced/9b870d72-791b-4e26-ae54-dbab0d96effb"
    "_b0711aae-0cbc-4be8-b27a-311b99f817c5/pptx/scripts/add_slide.py")
CLEAN = ADD_SLIDE.parent / "clean.py"

TITLE = "CUSTOMER REVENUE INTELLIGENCE"
SUBTITLE = ("An Interactive Data Science Platform for Customer Segmentation, "
            "Revenue Prediction and Business Growth")

# Candidate details, taken from the bonafide certificate.  The UID is not
# printed on that certificate, so it stays a placeholder.
STUDENT = "Swagata Das"
UID = "[TO BE FILLED]"
PROGRAMME = "MBA - Data Science and AI (3rd Semester)"
INSTITUTE = "Apex Institute of Management"
UNIVERSITY = "Chandigarh University"
GUIDE = "Kuldeep Dubey"
COMPANY = "Tutorsuite Technologies LLP, Kolkata"
INTERNSHIP = "Summer Internship (1st June - 12th July)"
BATCH = "MBA 2023-25"

# which template slide each output slide is cloned from
SOURCES = [1, 3, 3, 2, 3, 3, 3, 2, 3, 2, 2, 3, 3, 2, 3, 2, 2, 3, 3, 3, 12, 13]

ACCENT = RGBColor(0xC0, 0x00, 0x00)     # the template's red
HEAD_TEXT = RGBColor(0xFF, 0xFF, 0xFF)
BODY_TEXT = RGBColor(0x1A, 0x1A, 0x1A)
BAND = RGBColor(0xF2, 0xF2, 0xF2)

F: dict = {}


# --------------------------------------------------------------------------
# number formatting - identical to the report's helpers
# --------------------------------------------------------------------------
def rs(x, dec=2):
    return "Rs " + f"{float(x):,.{dec}f}"


def cr(x, dec=2):
    return f"Rs {float(x) / 1e7:,.{dec}f} Cr"


def lakh(x, dec=2):
    return f"Rs {float(x) / 1e5:,.{dec}f} L"


def n(x, dec=0):
    return f"{float(x):,.{dec}f}"


def pc(x, dec=2):
    return f"{float(x):.{dec}f}%"


def pcf(x, dec=2):
    return f"{float(x) * 100:.{dec}f}%"


def row_by(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    raise KeyError(f"{key}={value}")


def fig(*parts) -> Path:
    p = FIG.joinpath(*parts)
    if not p.exists():
        raise FileNotFoundError(p)
    return p


# --------------------------------------------------------------------------
# template-preserving text helpers
# --------------------------------------------------------------------------
def _proto(tf):
    """First paragraph that carries a run - used as the formatting model."""
    for para in tf.paragraphs:
        if para.runs:
            return para
    return tf.paragraphs[0]


def set_lines(shape, lines):
    """Replace a shape's text, keeping the template's own run formatting.

    `lines` is a list of strings, or of (text, level) / (text, level, bold)
    tuples.  An empty string produces a blank spacer line.
    """
    tf = shape.text_frame
    proto = _proto(tf)
    proto_xml = copy.deepcopy(proto._p)
    parent = proto._p.getparent()
    for p in list(parent):
        if p.tag.endswith("}p"):
            parent.remove(p)

    for _ in lines:
        parent.append(copy.deepcopy(proto_xml))

    # re-read through python-pptx so runs are addressable
    for para, item in zip(tf.paragraphs, lines):
        bold = None
        level = 0
        if isinstance(item, tuple):
            text, level = item[0], item[1]
            if len(item) > 2:
                bold = item[2]
        else:
            text = item
        runs = para.runs
        for extra in runs[1:]:
            extra._r.getparent().remove(extra._r)
        run = para.runs[0]
        run.text = text
        if bold is not None:
            run.font.bold = bold
        para.level = level
    return tf


def set_title(slide, name, text):
    """Title text at a size that clears the institute logo / its own box."""
    shape = by_name(slide, name)
    set_lines(shape, [text])
    wide = name.startswith("Title 1")          # full-width content layout
    if wide:
        size = 34 if len(text) <= 22 else (30 if len(text) <= 26 else 27)
    else:                                      # narrow column, visual layout
        size = 26 if len(text) <= 24 else (22 if len(text) <= 36 else 20)
    for para in shape.text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(size)
    return shape


def set_body(slide, name, lines, size=None):
    """Body text; `size` forces a point size (used on the narrow column)."""
    shape = by_name(slide, name)
    set_lines(shape, lines)
    if size:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                run.font.size = Pt(size)
    return shape


def clear_visual(slide):
    shape = by_name(slide, "Content Placeholder 2")
    shape.text_frame.clear()
    shape.text_frame.paragraphs[0].text = ""
    return shape


def by_name(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(f"{name} not on slide")


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def add_picture(slide, path, left, top, max_w, max_h):
    """Insert a picture scaled to fit the box, centred in it."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    scale = min(max_w / w, max_h / h)
    pw, ph = w * scale, h * scale
    return slide.shapes.add_picture(
        str(path), Emu(int(left + (max_w - pw) / 2)),
        Emu(int(top + (max_h - ph) / 2)), Emu(int(pw)), Emu(int(ph)))


def add_two_pictures(slide, top_path, bottom_path, gap=Cm(0.5)):
    """Two wide charts stacked inside the template's visual rectangle."""
    half = (VIS_H - gap) / 2
    add_picture(slide, top_path, VIS_L, VIS_T, VIS_W, half)
    add_picture(slide, bottom_path, VIS_L, VIS_T + half + gap, VIS_W, half)


def add_table(slide, headers, rows, left, top, width, height,
              font_size=11, head_size=11, col_widths=None,
              align_right=()):
    shape = slide.shapes.add_table(len(rows) + 1, len(headers),
                                   Emu(int(left)), Emu(int(top)),
                                   Emu(int(width)), Emu(int(height)))
    table = shape.table
    table.first_row = True
    if col_widths:
        total = sum(col_widths)
        for i, w in enumerate(col_widths):
            table.columns[i].width = Emu(int(width * w / total))
    for j, head in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = str(head)
        para = cell.text_frame.paragraphs[0]
        para.runs[0].font.size = Pt(head_size)
        para.runs[0].font.bold = True
        para.runs[0].font.name = "Arial"
        para.runs[0].font.color.rgb = HEAD_TEXT
        cell.fill.solid()
        cell.fill.fore_color.rgb = ACCENT
        cell.margin_left = cell.margin_right = Cm(0.12)
        cell.margin_top = cell.margin_bottom = Cm(0.04)
    for i, row in enumerate(rows, start=1):
        for j, value in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(value) if str(value).strip() else " "
            para = cell.text_frame.paragraphs[0]
            para.runs[0].font.size = Pt(font_size)
            para.runs[0].font.name = "Arial"
            para.runs[0].font.color.rgb = BODY_TEXT
            if j in align_right:
                from pptx.enum.text import PP_ALIGN
                para.alignment = PP_ALIGN.RIGHT
            cell.fill.solid()
            cell.fill.fore_color.rgb = (
                RGBColor(0xFF, 0xFF, 0xFF) if i % 2 else BAND)
            cell.margin_left = cell.margin_right = Cm(0.12)
            cell.margin_top = cell.margin_bottom = Cm(0.03)
    return table


# --------------------------------------------------------------------------
# build the skeleton: clone template slides into the running order
# --------------------------------------------------------------------------
def build_skeleton() -> Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    unpacked = WORK / "unpacked"
    with zipfile.ZipFile(TEMPLATE) as z:
        z.extractall(unpacked)

    created = []
    for src in SOURCES:
        out = subprocess.run(
            [sys.executable, str(ADD_SLIDE), str(unpacked) + "/",
             f"slide{src}.xml"], capture_output=True, text=True)
        if out.returncode:
            raise RuntimeError(out.stderr)
        created.append(int(re.search(r"slide(\d+)\.xml from",
                                     out.stdout).group(1)))

    rels = (unpacked / "ppt" / "_rels" / "presentation.xml.rels").read_text()
    by_num = {int(num): rid for rid, num in re.findall(
        r'Id="(rId\d+)"[^>]*Target="slides/slide(\d+)\.xml"', rels)}
    pres = unpacked / "ppt" / "presentation.xml"
    xml = pres.read_text()
    lst = "".join(f'<p:sldId id="{256 + i}" r:id="{by_num[num]}"/>'
                  for i, num in enumerate(created))
    pres.write_text(re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>",
                           f"<p:sldIdLst>{lst}</p:sldIdLst>", xml, flags=re.S))
    subprocess.run([sys.executable, str(CLEAN), str(unpacked) + "/"],
                   check=True, capture_output=True)

    skeleton = WORK / "skeleton.pptx"
    subprocess.run(["zip", "-qXr", str(skeleton), "."], cwd=unpacked,
                   check=True)
    return skeleton


# --------------------------------------------------------------------------
# geometry of the template's content area
# --------------------------------------------------------------------------
BOX_L, BOX_T = Cm(2.33), Cm(5.08)          # inside "Rectangle 4"
BOX_W, BOX_H = Cm(29.21), Cm(12.14)
VIS_L, VIS_T = Cm(15.1), Cm(2.6)           # inside "Rectangle 1"
VIS_W, VIS_H = Cm(16.0), Cm(14.9)
TXT_SIZE = 11.5                            # left column on the visual layout


def add_note_box(slide, lines, top, height, left=None, width=None,
                 size=12):
    """A plain text box inside the content rectangle, for text that has to
    sit below a table."""
    from pptx.util import Pt as _Pt
    box = slide.shapes.add_textbox(
        Emu(int(left if left is not None else BOX_L + Cm(0.5))), Emu(int(top)),
        Emu(int(width if width is not None else BOX_W - Cm(1.0))),
        Emu(int(height)))
    tf = box.text_frame
    tf.word_wrap = True
    for i, line in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = para.add_run()
        run.text = line
        run.font.size = _Pt(size)
        run.font.name = "Arial"
        run.font.color.rgb = BODY_TEXT
        para.space_after = _Pt(4)
    return box


# ==========================================================================
# SLIDE CONTENT
# ==========================================================================
def slide_title(s):
    """1 - title slide (template slide 1)."""
    topic = by_name(s, "TextBox 52")
    set_lines(topic, [TITLE])
    topic.left, topic.top = Cm(9.7), Cm(12.5)
    topic.width, topic.height = Cm(21.8), Cm(1.5)
    for para in topic.text_frame.paragraphs:
        for run in para.runs:
            run.font.size = Pt(24)
            run.font.name = "Times New Roman"
            run.font.bold = True
    box = by_name(s, "TextBox 1")
    set_lines(box, [SUBTITLE])
    box.left, box.top = Cm(11.2), Cm(14.0)
    box.width, box.height = Cm(19.5), Cm(1.5)
    box.text_frame.word_wrap = True
    for para in box.text_frame.paragraphs:
        para.alignment = PP_ALIGN.CENTER
        for run in para.runs:
            run.font.size = Pt(12)
            run.font.name = "Times New Roman"
            run.font.bold = False
    set_lines(by_name(s, "TextBox 25"), [
        f"{INSTITUTE.upper()}, {UNIVERSITY.upper()}",
        f"Programme: {PROGRAMME}",
        INTERNSHIP,
        f"Submitted by: {STUDENT}   |   UID: {UID}",
        f"Under the guidance of: {GUIDE}",
        f"Internship Organization: {COMPANY}",
        f"Academic Year: {BATCH}",
    ])
    tf = by_name(s, "TextBox 25").text_frame
    sizes = [19, 16, 16, 15, 14, 14, 14]
    for para, size in zip(tf.paragraphs, sizes):
        for run in para.runs:
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"
            run.font.bold = size >= 16
    notes(s, "Good morning. I am Swagata Das, MBA Data Science and AI at "
             "Apex Institute of Management, Chandigarh University. This is "
             "my summer internship project, carried out at Tutorsuite "
             "Technologies LLP, Kolkata, under the guidance of Kuldeep "
             "Dubey. The project builds one platform that takes customer "
             "transaction data through segmentation, value analysis, "
             "prediction and forecasting to a business decision.")


def slide_introduction(s):
    d = F["dataset"]
    set_title(s, "Title 1", "Introduction")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Retail and e-commerce businesses record transaction data far "
         "faster than they convert it into decisions.", 0),
        ("Revenue is reported in aggregate - by month, category and region "
         "- but the questions that drive growth are customer-level: who "
         "matters most, who is going quiet, what will they spend next.", 0),
        ("Customer value is concentrated, so identifying and protecting "
         "high-value customers is more economical than acquiring new ones.",
         0),
        ("Planning needs a forward view: predicted customer revenue and a "
         "forecast of company revenue with an honest error range.", 0),
        ("An integrated analytics platform is needed so segmentation, "
         "value analysis, prediction and forecasting all use one validated "
         "dataset and one definition of revenue.", 0),
        (f"This project implements that platform on {n(d['clean_rows'])} "
         f"validated order lines covering {n(d['customers_purchasing'])} "
         f"customers over {d['months']} months.", 0),
    ])
    notes(s, "Frame the business problem first. Aggregate reporting cannot "
             "tell a month carried by a few large customers from one built "
             "on a broad base, so it cannot guide retention spend. Likely "
             "viva question: why customer-level analytics rather than "
             "reporting? Answer: because the decisions - who to retain, "
             "who to grow - are taken at customer level.")


def slide_organization(s):
    d = F["dataset"]
    set_title(s, "Title 1", "About the Organization")
    set_lines(by_name(s, "Content Placeholder 2"), [
        (f"Internship organization: {COMPANY}.", 0, True),
        (f"Internship period: {INTERNSHIP.replace('Summer Internship ', '').strip('()')}, "
         f"under the guidance of {GUIDE}.", 0),
        ("", 0),
        ("Academic project based on a synthetic e-commerce transaction "
         "dataset.", 0, True),
        ("The dataset was generated programmatically for academic "
         "demonstration. It does not describe any real company, customer "
         "or transaction, including the internship organization.", 0),
        (f"It is reproducible from a fixed seed ({d['seed']}), which allows "
         "every result in this presentation to be regenerated and checked.",
         0),
        ("No company history, revenue, client or operational information "
         "is presented, because none is documented for this project.", 0),
    ])
    notes(s, "Be explicit and unembarrassed about this: the data is "
             "synthetic. Say why it is a strength for an academic project - "
             "no confidentiality constraint, a known ground truth to audit "
             "the cleaning against, and full reproducibility. The methods "
             "are exactly those you would apply to real data. Viva "
             "question: would your results hold on real data? Answer: the "
             "method transfers, the specific numbers do not.")


def slide_about_topic(s):
    set_title(s, "Title 7", "About Customer Revenue Intelligence")
    set_body(s, "Text Placeholder 3", [
        ("Customer revenue intelligence turns raw transactions into "
         "decisions by moving up a chain: who the customer is, what they "
         "are worth, and what they will do next.", 0),
        ("Each stage consumes the validated output of the one before it, "
         "so one revenue definition holds end to end.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_picture(s, fig("report", "graphical_abstract.png"),
                VIS_L, VIS_T, VIS_W, VIS_H)
    notes(s, "Walk the chain out loud: customer data, customer "
             "understanding, segmentation, value analysis, prediction, "
             "forecasting, business decision. The point to make is that "
             "each arrow is a real module in the project, not a concept - "
             "the diagram is generated from the actual pipeline.")


def slide_literature(s):
    set_title(s, "Title 1", "Review of Related Literature")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Six strands of published work inform the design. Full APA "
         "citations are on the References slide.", 0),
    ])
    add_table(
        s,
        ["Area", "Key work", "Method", "Relevance to this project"],
        [["RFM analysis", "Hughes (1994); Fader et al. (2005)",
          "Quintile customer scoring", "Rule-based customer value segments"],
         ["Segmentation", "MacQueen (1967); Rousseeuw (1987)",
          "K-Means; silhouette", "Unsupervised customer groups"],
         ["Customer value", "Gupta et al. (2006); Fader et al. (2005)",
          "CLV modelling", "Historical vs estimated forward value"],
         ["Prediction", "Hastie et al. (2009); Breiman (2001)",
          "Regression and ensembles", "Next-quarter customer revenue"],
         ["Forecasting", "Hyndman & Athanasopoulos (2021); Theta (2000)",
          "ETS, ARIMA, Theta", "Monthly revenue planning"],
         ["BI delivery", "Kimball & Ross (2013); Few (2006)",
          "Star schema; dashboard design", "Power BI model and application"]],
        BOX_L + Cm(0.5), BOX_T + Cm(2.2), BOX_W - Cm(1.0), Cm(8.6),
        font_size=11, col_widths=[2.0, 3.4, 2.6, 3.4])
    notes(s, "Do not claim novelty in any single technique - all six are "
             "established. What the literature gives you is the discipline: "
             "Rousseeuw for choosing K, Hyndman for insisting a forecast "
             "beat a naive benchmark, Gupta for separating measured "
             "historical value from estimated forward value. Viva question: "
             "which paper justified your K? Answer: silhouette from "
             "Rousseeuw, applied only after stability rules fixed in "
             "advance.")


def slide_gap(s):
    au = F["audit"]
    set_title(s, "Title 1", "Research Gap & Significance")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("The practical gap", 0, True),
        ("Transaction data  ->  traditional reporting  ->  limited customer "
         "intelligence  ->  limited predictive capability.", 1),
        ("These techniques are well established individually, and prior "
         "research has combined several of them. What is rarely available "
         "in one reproducible workflow is all of them on one validated "
         "dataset with a single revenue definition.", 1),
        ("", 0),
        ("The integrated solution implemented here", 0, True),
        ("RFM  +  K-Means  +  Customer value  +  Revenue prediction  +  "
         "Forecasting  +  SQL  +  Power BI  +  Streamlit.", 1),
        ("Significance: every stage is re-runnable from a fixed seed, every "
         "metric is reconciled against an independent SQL implementation, "
         f"and the whole project passes an audit of {au['total']} checks "
         f"({au['passed']} pass, {au['failed']} fail).", 1),
    ])
    notes(s, "State the gap carefully - integration and traceability, not "
             "novelty of method. If asked what is new: one dataset and one "
             "revenue definition flowing through every stage, reconciled "
             "across Python, SQL and DAX, with an audit that tests the "
             "integration rather than asserting it.")


def slide_objectives(s):
    set_title(s, "Title 1", "Objectives of the Study")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("1.  Generate and validate the dataset, and clean it against "
         "explicit business rules", 0),
        ("2.  Characterise the revenue base through exploratory data "
         "analysis", 0),
        ("3.  Score every purchasing customer on Recency, Frequency and "
         "Monetary value", 0),
        ("4.  Segment customers independently using K-Means clustering", 0),
        ("5.  Quantify historical customer value and estimate forward "
         "twelve-month value", 0),
        ("6.  Predict customer revenue for the following quarter", 0),
        ("7.  Forecast company-level monthly revenue with prediction "
         "intervals", 0),
        ("8.  Reproduce the principal metrics independently in SQL and "
         "reconcile them", 0),
        ("9.  Build a Power BI semantic model and dashboard specification",
         0),
        ("10.  Develop an interactive Streamlit application", 0),
        ("11.  Derive evidence-linked business recommendations", 0),
    ])
    notes(s, "All eleven objectives were implemented; none is aspirational. "
             "If asked which objective was hardest: objective 6, revenue "
             "prediction, because the target is zero-inflated - and that "
             "result is reported honestly rather than dressed up.")


def slide_methodology(s):
    set_title(s, "Title 7", "Research Methodology")
    set_body(s, "Text Placeholder 3", [
        ("Applied data science on quantitative transaction data: machine "
         "learning for segmentation and prediction, time-series analysis "
         "for forecasting, business intelligence for delivery.", 0),
        ("Three validation gates let a stage reject its own output: "
         "business rules, K-selection and the forecasting baseline test.",
         0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_picture(s, fig("report", "flowchart.png"), VIS_L, VIS_T, VIS_W,
                VIS_H)
    notes(s, "Emphasise the gates - they are what makes this a methodology "
             "rather than a sequence of scripts. Gate 1: no analysis until "
             "every business rule returns zero failing rows. Gate 2: K must "
             "satisfy rules fixed before the results were seen. Gate 3: a "
             "forecast model must beat both naive baselines or it is "
             "rejected.")


def slide_dataset(s):
    d, q = F["dataset"], F["quality"]
    set_title(s, "Title 1", "Dataset & Data Preprocessing")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Raw data -> missing values -> duplicates -> data types -> "
         "business rules -> outliers -> clean dataset -> feature "
         "engineering.", 0),
    ])
    add_table(
        s,
        ["Dataset property", "Value", "Cleaning rule",
         "Rows failing before / after"],
        [["Raw extract", f"{n(d['raw_rows'])} lines, {d['raw_cols']} columns",
          "Missing value", f"{n(q['rules'][0]['Rows_Before'])} / 0"],
         ["Cleaned dataset",
          f"{n(d['clean_rows'])} lines, {d['clean_cols']} columns",
          "Invalid or non-ISO date",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'non_iso_or_invalid_date')['Rows_Before'])} / 0"],
         ["Duplicates removed", n(d["duplicates_removed"]),
          "Non-numeric value",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'non_numeric_value')['Rows_Before'])} / 0"],
         ["Customers",
          f"{n(d['customers_registered'])} registered, "
          f"{n(d['customers_purchasing'])} purchasing",
          "Discount out of range",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'discount_out_of_range')['Rows_Before'])} / 0"],
         ["Products",
          f"{d['products']} in {d['categories']} categories",
          "Revenue mismatch",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'revenue_mismatch')['Rows_Before'])} / 0"],
         ["Geography",
          f"{d['cities']} cities, {d['states']} states, {d['regions']} regions",
          "Invalid category value",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'invalid_category_value')['Rows_Before'])} / 0"],
         ["Period", f"{d['start']} to {d['end']} ({d['months']} months)",
          "Age out of range",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'age_out_of_range')['Rows_Before'])} / 0"],
         ["Orders", f"{n(d['orders_all'])} across all statuses",
          "Quantity not positive",
          f"{n(row_by(q['rules'], 'Validation_Rule', 'quantity_not_positive')['Rows_Before'])} / 0"]],
        BOX_L + Cm(0.5), BOX_T + Cm(1.9), BOX_W - Cm(1.0), Cm(9.0),
        font_size=10.5, col_widths=[2.4, 3.6, 2.6, 2.4])
    notes(s, "Revenue is computed on delivered order lines only; returned "
             "and cancelled lines are kept and analysed separately as lost "
             "value. That single rule, applied identically in Python, SQL "
             "and DAX, is what makes the three implementations "
             "reconcilable. Every cleaning rule returns zero failing rows "
             "after treatment - a rule that does not is treated as a "
             "failure of the cleaning stage, not an acceptable residue.")


def slide_eda(s):
    kpi, eda = F["kpi"], F["eda"]
    y = eda["by_year"]
    top20 = row_by(eda["concentration"], "top_pct", 20)
    set_title(s, "Title 7", "Exploratory Data Analysis")
    set_body(s, "Text Placeholder 3", [
        (f"Delivered revenue {cr(kpi['revenue'])} at {pcf(kpi['margin'])} "
         f"margin, {n(kpi['orders'])} orders, AOV {rs(kpi['aov'], 0)}.", 0),
        (f"Revenue grew {pc(y[1]['revenue_yoy_growth_pct'], 1)} then "
         f"{pc(y[-1]['revenue_yoy_growth_pct'], 1)} while margin rose to "
         f"{pc(y[-1]['profit_margin_pct'])} - growth is not bought with "
         "margin.", 0),
        (f"The top 20% of customers produce {pc(top20['pct_of_revenue'])} "
         "of revenue.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_two_pictures(s, fig("monthly_revenue_trend.png"),
                     fig("category_revenue_vs_profit.png"))
    notes(s, "Each chart answers a business question. This one answers "
             "'is the business growing, and is it buying that growth with "
             "margin?' - the answer is yes and no respectively. October is "
             "the strongest month in all three years, which is the clearest "
             "seasonal signal the series carries, but with 36 observations "
             "the formal seasonality test does not confirm a stable "
             "pattern.")


def slide_segmentation(s):
    rfm, km = F["rfm"], F["kmeans"]
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    hv = km["summary"][0]
    ari = row_by(km["agreement"], "Measure",
                 "Adjusted Rand Index (RFM segment vs cluster)")
    set_title(s, "Title 7", "Customer Intelligence - RFM & K-Means")
    set_body(s, "Text Placeholder 3", [
        (f"RFM scores {n(rfm['customers_scored'])} customers on recency, "
         f"frequency and monetary value into {rfm['segments']} rule-based "
         f"segments. Champions: {pc(champ['Customer_%'], 1)} of customers, "
         f"{pc(champ['Revenue_%'], 1)} of revenue.", 0),
        (f"K-Means on the same features selected K = {km['k']} "
         f"(silhouette {km['overall_silhouette']:.3f}). Cluster 0 is "
         f"{pc(hv['Customer_%'], 1)} of customers and "
         f"{pc(hv['Revenue_%'], 1)} of revenue.", 0),
        (f"Agreement between the two schemes: ARI {ari['Value']:.4f}.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_two_pictures(s, fig("rfm_revenue_contribution.png"),
                     fig("cluster_distribution.png"))
    notes(s, "The two schemes are independent: RFM is rules, K-Means is "
             "unsupervised. They agree substantially on the high-value "
             "group and diverge in the middle of the base, which is itself "
             "a finding - it shows where the rule boundaries are "
             "arbitrary. Viva question: why K = 4? Answer: three rules were "
             "fixed before seeing results - K at least 3, no cluster below "
             "5% of the base, bootstrap stability ARI at least 0.90 - and "
             "among the eligible values K = 4 had the highest silhouette.")


def slide_clv(s):
    clv = F["clv"]
    set_title(s, "Title 1", "Customer Lifetime Value")
    set_lines(by_name(s, "Content Placeholder 2"), [
        (f"Historical value (measured): {cr(clv['historical_profit_total'])} "
         f"of delivered profit on {cr(clv['historical_revenue_total'])} of "
         f"revenue; mean {rs(clv['mean_historical_profit'], 0)} against "
         f"median {rs(clv['median_historical_profit'], 0)} per customer.",
         0),
        (f"Estimated forward value (predicted): a "
         f"{clv['metadata']['selected_model'].lower()} trained out of time "
         "on eight behavioural features, predicting delivered profit over "
         "the next twelve months. The two are reported separately and are "
         "never added together.", 0),
    ])
    add_table(
        s,
        ["Forward-value model", "MAE", "RMSE", "R2", "Spearman", "Selected"],
        [[m["Model"], rs(m["MAE"], 0), rs(m["RMSE"], 0), f"{m['R2']:.4f}",
          f"{m['Spearman']:.4f}", "Yes" if m.get("Selected") else ""]
         for m in clv["model_comparison"]],
        BOX_L + Cm(0.5), BOX_T + Cm(4.3), BOX_W - Cm(1.0), Cm(4.4),
        font_size=11, col_widths=[4.0, 1.5, 1.5, 1.2, 1.4, 1.2],
        align_right=(1, 2, 3, 4))
    add_note_box(s, [
        f"Value drivers by permutation importance: "
        f"{', '.join(r['Feature'] for r in clv['feature_importance'][:4])}.",
        f"{n(clv['estimate_methods']['ML model (active in last 12 months)'])} "
        f"customers scored by the model, "
        f"{n(clv['estimate_methods']['Group average (no order in last 12 months)'])} "
        f"by group average. {clv['at_risk']} high-value customers are "
        f"inactive for 180+ days, holding {lakh(clv['at_risk_revenue'])} of "
        f"historical revenue.",
    ], top=BOX_T + Cm(9.0), height=Cm(2.6))
    notes(s, "Be precise about the distinction the examiner will probe: "
             "historical value is measured from delivered profit already "
             "earned; forward value is an estimate with error. The model's "
             "R-squared of 0.2705 with a Spearman of 0.4869 means it ranks "
             "customers considerably better than it predicts their exact "
             "value - so it is used as a prioritisation instrument, not as "
             "a promise of any individual customer's spend.")


def slide_prediction(s):
    pred = F["prediction"]
    tm = pred["test_metrics"]
    set_title(s, "Title 1", "Revenue Prediction")
    set_lines(by_name(s, "Content Placeholder 2"), [
        (f"Target: each customer's delivered revenue in the next quarter. "
         f"Panel of {n(pred['panel_rows'])} customer-quarter rows with "
         f"{pred['n_features']} features computed strictly before the "
         "target quarter began.", 0),
        (f"Out-of-time split (not random): {n(pred['train_rows'])} train / "
         f"{n(pred['val_rows'])} validation / {n(pred['test_rows'])} test "
         "rows.", 0),
    ])
    add_table(
        s,
        ["Model tested", "Type", "MAE", "RMSE", "R2", "WAPE", "Selected"],
        [[m["Model"], m["Type"], rs(m["MAE"], 0), rs(m["RMSE"], 0),
          f"{m['R2']:.4f}", pc(m["WAPE_%"], 1),
          "Yes" if m.get("Selected") else ""]
         for m in pred["comparison"]],
        BOX_L + Cm(0.5), BOX_T + Cm(3.9), BOX_W - Cm(1.0), Cm(4.2),
        font_size=10, head_size=10,
        col_widths=[4.2, 1.6, 1.5, 1.5, 1.2, 1.3, 1.2],
        align_right=(2, 3, 4, 5))
    add_note_box(s, [
        f"Selected: {pred['model']} by the rule fixed in advance - "
        f"{pred['selection_rule']}.",
        f"Most important features (permutation): "
        f"{', '.join(r['Feature'] for r in pred['importance'][:4])}.",
        f"Honest reading: the model beats every baseline but is weak in "
        f"absolute terms (R2 {tm['R2']:.4f}), because "
        f"{pcf(pred['zero_actual_share'], 1)} of customer-quarters have a "
        f"zero actual value. Total bias {pc(tm['Total_Bias_%'], 2)}, so it "
        f"is usable at portfolio level, not for one customer.",
    ], top=BOX_T + Cm(8.5), height=Cm(3.0), size=11)
    notes(s, "Do not oversell this slide - the examiner will respect the "
             "honesty more than a high number. The model is better than "
             "the naive previous-quarter baseline on every metric, but "
             "explains only about 5.6% of the variance in individual "
             "outcomes. The reason is structural zero-inflation: more than "
             "half of customer-quarters have no order at all. The correct "
             "fix, stated in future scope, is a two-stage model: will the "
             "customer order, and if so how much.")


def slide_forecasting(s):
    fc = F["forecast"]
    fm = fc["metrics"]
    set_title(s, "Title 7", "Sales Forecasting")
    set_body(s, "Text Placeholder 3", [
        ("Forecasting is company-level monthly revenue; prediction is per "
         "customer per quarter. They are different tasks.", 0),
        (f"Naive, seasonal naive, ETS, ARIMA/SARIMA and Theta were tested "
         f"on {fc['series_months']} months. Selected: {fc['model']}, "
         f"backtest mean MAPE {pc(fm['backtest_mean_MAPE_%'], 2)}.", 0),
        (f"{fc['horizon']}-month horizon: {cr(fc['future_total'])}, 80% "
         f"interval {cr(fc['future_lower80'])} to "
         f"{cr(fc['future_upper80'])}.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_picture(s, fig("forecasting", "actual_vs_forecast.png"), VIS_L,
                VIS_T, VIS_W, VIS_H)
    notes(s, "Make the distinction between prediction and forecasting "
             "explicitly - it is a standard viva question. Then defend the "
             "model choice: Theta was selected because it had the lowest "
             "mean backtest error and beat both naive baselines on test "
             "MAE, which was a rule set before the results were seen. "
             "Quote the backtest MAPE, not the flattering single-split "
             "test MAPE. The interval is wide because the history is short "
             "and the model is univariate - it uses no price, promotion or "
             "holiday input.")


def slide_sql(s):
    sq = F["sql"]
    set_title(s, "Title 1", "SQL-Based Business Analytics")
    set_lines(by_name(s, "Content Placeholder 2"), [
        (f"A normalised SQLite database of {sq['tables']} tables and "
         f"{sq['views']} views, with {sq['queries']} analytical queries "
         f"({sq['analysis_queries']} analysis, {sq['business_queries']} "
         f"business). All {sq['validation_passed']}/"
         f"{sq['validation_checks']} validation checks and "
         f"{sq['quality_checks']} data-quality checks pass.", 0),
        ("Techniques used: JOIN, GROUP BY, common table expressions, "
         "window functions, self-joins, conditional aggregation and "
         "ranking.", 0),
    ])
    add_table(
        s,
        ["Business question answered in SQL", "Result computed",
         "Source query"],
        [[f["Area"], f["Finding (computed by SQL)"], f["Source query"]]
         for f in sq["key_findings"][:6]],
        BOX_L + Cm(0.5), BOX_T + Cm(3.2), BOX_W - Cm(1.0), Cm(7.4),
        font_size=10, col_widths=[2.2, 7.0, 2.2])
    add_note_box(s, [
        "This layer is an independent implementation: written against the "
        "same definitions in a different language, so agreement with the "
        "Python pipeline is evidence rather than a tautology.",
    ], top=BOX_T + Cm(10.8), height=Cm(1.2))
    notes(s, "The purpose of the SQL layer is reconciliation, not "
             "duplication. Revenue, profit, margin, order count, customer "
             "count and AOV are recomputed here from the normalised tables "
             "and agree with the Python pipeline to the paisa - which is "
             "what allows the dashboard and the application to quote the "
             "same figures. Be ready to name the window functions used: "
             "ROW_NUMBER and RANK for top-N customers and products, and "
             "cumulative sums for the concentration curve.")


def slide_powerbi(s):
    pb = F["powerbi"]
    set_title(s, "Title 7", "Power BI Executive Dashboard")
    set_body(s, "Text Placeholder 3", [
        (f"Star schema: {pb['tables']} tables, {pb['relationships']} "
         f"relationships, {pb['measures']} DAX measures in "
         f"{pb['folders']} folders, nine pages specified.", 0),
        (f"All {pb['validation_matched']}/{pb['validation_rows']} measure "
         f"validations match SQL; all {pb['consistency_total']} "
         "consistency checks pass.", 0),
        ("Power BI Desktop is Windows-only and was unavailable, so the "
         "page shown is a design mockup rendered from the real data - not "
         "a screenshot.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_picture(s, fig("powerbi", "mockups",
                       "01_executive_overview_mockup.png"),
                VIS_L, VIS_T, VIS_W, VIS_H)
    notes(s, "Say plainly that this is a design mockup, not a screenshot, "
             "and why - Power BI Desktop is Windows-only and the project "
             "was built on Linux. Then say what IS complete: the semantic "
             "model, the 84 DAX measures every one of which was validated "
             "against its SQL equivalent, the Power Query scripts, the "
             "theme and a build guide. Anyone with Power BI Desktop can "
             "build the report from those artefacts in an afternoon. "
             "Claiming a screenshot you do not have is the one thing that "
             "would undermine the whole deck.")


def slide_streamlit(s):
    stl = F["streamlit"]
    set_title(s, "Title 7", "Interactive Streamlit Data Science Platform")
    set_body(s, "Text Placeholder 3", [
        (f"A working {stl['pages']}-page application with interactive "
         "filters, Plotly charts, CSV download on every table and a data "
         "explorer.", 0),
        ("It loads the persisted models rather than refitting, and "
         "computes no metric of its own - every number comes from the "
         "pipeline's outputs.", 0),
        (f"Tested headlessly: {stl['tests_passed']}/{stl['tests']} checks "
         "pass. The image is a real screenshot.", 0),
    ], size=TXT_SIZE)
    clear_visual(s)
    add_picture(s, fig("streamlit", "02_executive_overview.png"), VIS_L,
                VIS_T, VIS_W, VIS_H)
    notes(s, "This is a real running application, and the image is a real "
             "screenshot of it - offer to demonstrate it live if the "
             "examiner wants. Emphasise the architectural point: the app "
             "is a presentation layer only. It loads the same persisted "
             "models and the same outputs the pipeline wrote, so a number "
             "on screen cannot drift from the number in the report.")


def slide_findings(s):
    eda, clv, rfm = F["eda"], F["clv"], F["rfm"]
    top10 = row_by(eda["concentration"], "top_pct", 10)
    top20 = row_by(eda["concentration"], "top_pct", 20)
    rep = row_by(eda["repeat"], "customer_group", "Repeat (2+ orders)")
    cat = eda["by_category"]
    best = max(cat, key=lambda c: c["profit_margin_pct"])
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    set_title(s, "Title 1", "Findings and Suggestions")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Key findings, and the recommendation each one supports:", 0),
    ])
    add_table(
        s,
        ["Finding (from project output)", "Business implication",
         "Recommendation"],
        [[f"Top 10% of customers produce {pc(top10['pct_of_revenue'])} of "
          f"revenue; top 20% produce {pc(top20['pct_of_revenue'])}",
          "Losing a few large customers costs more than a month of "
          "acquisition",
          "Give the top decile a named owner and review it monthly"],
         [f"{clv['at_risk']} high-value customers inactive 180+ days, "
          f"holding {lakh(clv['at_risk_revenue'])} of revenue",
          "Value already earned is quietly at risk",
          "Work the list as a contact campaign; record the outcome"],
         [f"Champions are {pc(champ['Customer_%'], 1)} of customers but "
          f"{pc(champ['Revenue_%'], 1)} of revenue",
          "A small group carries the business",
          "Protect and grow Champions before chasing new customers"],
         [f"Repeat customers are {pc(rep['pct_of_customers'], 1)} of the "
          f"base and {pc(rep['pct_of_revenue'], 1)} of revenue",
          "The second order is where value is created",
          "Target the first-to-second order conversion"],
         [f"{cat[0]['category']} is {pc(cat[0]['revenue_share_pct'])} of "
          f"revenue at {pc(cat[0]['profit_margin_pct'])} margin; "
          f"{best['category']} earns {pc(best['profit_margin_pct'])}",
          "Volume leader and margin leader are different assets",
          "Manage category mix rather than a single revenue target"],
         [f"Zero-discount band returns the best margin in "
          f"{eda['zero_discount_best_in']} of {eda['categories_tested']} "
          f"categories",
          "Discounting is costing margin (association, not proven cause)",
          "Run a controlled discount experiment before changing policy"]],
        BOX_L + Cm(0.5), BOX_T + Cm(1.6), BOX_W - Cm(1.0), Cm(9.6),
        font_size=9.5, col_widths=[3.6, 3.2, 3.6])
    notes(s, "Every row here is traceable to an output file and is "
             "reproduced in the application's recommendations page - "
             "eighteen recommendations in total, six shown here. The one "
             "to be careful about in viva is the discount row: the "
             "relationship is an association measured on observed orders, "
             "not a causal claim, which is exactly why the recommendation "
             "is to run an experiment rather than to cut discounts.")


def slide_future_scope(s):
    set_title(s, "Title 1", "Future scope of the study")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Validate the pipeline on a real transaction dataset under an "
         "appropriate data-protection agreement, and compare the segment "
         "structure that emerges with the one reported here.", 0),
        ("Define an operational inactivity label with the business, and "
         "convert the present recency flag into a supervised model that "
         "can be evaluated against it.", 0),
        ("Reframe next-quarter prediction as a two-stage problem - will "
         "the customer order at all, and if so how much - to address the "
         "zero-inflation that limits the present model.", 0),
        ("Extend the forecast with external regressors: promotion "
         "calendar, price index and holiday effects, benchmarked against "
         "the current univariate backtest.", 0),
        ("Run a controlled discount experiment to establish whether the "
         "observed discount-margin association is causal.", 0),
        ("Operationalise the pipeline with scheduled re-runs, drift "
         "monitoring on the input distributions and model-performance "
         "tracking against realised outcomes.", 0),
        ("Complete the Power BI build on a Windows machine from the "
         "supplied semantic model, measures and build guide.", 0),
    ])
    notes(s, "Frame future scope as the honest continuation of the "
             "limitations, not as a wish list. Each item answers a "
             "specific weakness named in the report: synthetic data, no "
             "churn label, zero-inflation, a univariate forecast, "
             "association without causation, no monitoring, and Power BI "
             "not rendered in Desktop.")


def slide_conclusion(s):
    d, kpi = F["dataset"], F["kpi"]
    km, fc, au = F["kmeans"], F["forecast"], F["audit"]
    code = F["code"]
    set_title(s, "Title 1", "Conclusion")
    set_lines(by_name(s, "Content Placeholder 2"), [
        (f"The project converts {n(d['clean_rows'])} validated transaction "
         f"lines into an integrated decision-support platform, carrying "
         "one dataset and one revenue definition through cleaning, "
         "exploratory analysis, dual segmentation, customer value "
         "analysis, prediction, forecasting, SQL analytics and two "
         "delivery surfaces.", 0),
        (f"Value is concentrated: the top 20% of customers hold "
         f"{pc(row_by(F['eda']['concentration'], 'top_pct', 20)['pct_of_revenue'])} "
         f"of {cr(kpi['revenue'])} in delivered revenue, and two "
         f"independent methods - RFM rules and K = {km['k']} clustering - "
         "identify substantially the same high-value group.", 0),
        (f"Reliability differs by horizon and is reported as such: monthly "
         f"company revenue forecasts to a backtest MAPE of "
         f"{pc(fc['metrics']['backtest_mean_MAPE_%'], 2)}, while "
         "individual customer revenue predicts weakly.", 0),
        (f"The integration is tested, not asserted: an audit of "
         f"{au['total']} checks returns {au['passed']} passes and "
         f"{au['failed']} failures across {code['python_files']} Python "
         f"modules, {code['sql_files']} SQL files and {code['notebooks']} "
         "executed notebooks.", 0),
        ("Every figure presented is read from the project's own output "
         "files, so the presentation, the report and the application "
         "cannot disagree.", 0),
    ])
    notes(s, "Close on the through-line: raw transactions in, business "
             "decisions out, with every step reproducible and every number "
             "traceable. If you are asked for the single most valuable "
             "outcome, say the concentration finding - it changes where "
             "the business spends effort - and note that two independent "
             "methods found it, which is why it can be trusted.")


def slide_references(s):
    set_title(s, "Title 1", "BIBLIOGRAPHY / REFERENCES")
    set_lines(by_name(s, "Content Placeholder 2"), [
        ("Books and Journal Articles (APA)", 0, True),
        ("Breiman, L. (2001). Random forests. Machine Learning, 45(1), "
         "5-32.", 1),
        ("Fader, P. S., Hardie, B. G. S., & Lee, K. L. (2005). RFM and "
         "CLV: Using iso-value curves for customer base analysis. Journal "
         "of Marketing Research, 42(4), 415-430.", 1),
        ("Gupta, S., Hanssens, D., Hardie, B., Kahn, W., Kumar, V., Lin, "
         "N., Ravishanker, N., & Sriram, S. (2006). Modeling customer "
         "lifetime value. Journal of Service Research, 9(2), 139-155.", 1),
        ("Hastie, T., Tibshirani, R., & Friedman, J. (2009). The elements "
         "of statistical learning (2nd ed.). Springer.", 1),
        ("Hughes, A. M. (1994). Strategic database marketing. Probus "
         "Publishing.", 1),
        ("Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: "
         "Principles and practice (3rd ed.). OTexts.", 1),
        ("Kimball, R., & Ross, M. (2013). The data warehouse toolkit (3rd "
         "ed.). Wiley.", 1),
        ("Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the "
         "interpretation and validation of cluster analysis. Journal of "
         "Computational and Applied Mathematics, 20, 53-65.", 1),
        ("Websites and Software Documentation", 0, True),
        ("Microsoft. (n.d.). Data Analysis Expressions (DAX) reference. "
         "https://learn.microsoft.com/en-us/dax/", 1),
        ("Streamlit Inc. (n.d.). Streamlit documentation. "
         "https://docs.streamlit.io/", 1),
        ("The complete reference list of 38 entries appears in the project "
         "report.", 0),
    ])
    notes(s, "These are the eleven most load-bearing of the 38 references "
             "in the report. Every one is a real, verifiable publication "
             "or official documentation - none was invented. If asked for "
             "the reference behind a specific choice, name it: Rousseeuw "
             "for silhouette, Hyndman for the naive-baseline rule, Gupta "
             "for separating historical from predicted value.")


def slide_thanks(s):
    set_title(s, "Title 1", "THANK YOU")
    box = s.shapes.add_textbox(Cm(2.0), Cm(13.6), Cm(29.0), Cm(3.4))
    tf = box.text_frame
    tf.word_wrap = True
    lines = [("Questions & Discussion", 20, True),
             (f"{STUDENT}  |  {PROGRAMME}", 14, False),
             (f"{TITLE}: {SUBTITLE}", 12, False)]
    for i, (text, size, bold) in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        run = para.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = "Times New Roman"
        run.font.color.rgb = BODY_TEXT
        para.space_after = Pt(4)
    notes(s, "Invite questions, and offer to run the Streamlit application "
             "live if the examiner would like to see the platform working.")


BUILDERS = [
    slide_title, slide_introduction, slide_organization, slide_about_topic,
    slide_literature, slide_gap, slide_objectives, slide_methodology,
    slide_dataset, slide_eda, slide_segmentation, slide_clv,
    slide_prediction, slide_forecasting, slide_sql, slide_powerbi,
    slide_streamlit, slide_findings, slide_future_scope, slide_conclusion,
    slide_references, slide_thanks,
]


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("building skeleton from the university template ...")
    skeleton = build_skeleton()
    prs = Presentation(str(skeleton))
    assert len(prs.slides._sldIdLst) == len(BUILDERS), "slide count mismatch"
    print(f"        {len(BUILDERS)} slides cloned")

    print("filling slide content ...")
    for build_slide, slide in zip(BUILDERS, prs.slides):
        build_slide(slide)
    prs.save(str(PPTX))
    print(f"        {PPTX.relative_to(ROOT)}")

    print("converting to PDF ...")
    out = subprocess.run(
        ["soffice", "--headless", "--norestore", "--convert-to", "pdf",
         "--outdir", str(OUT_DIR), str(PPTX)],
        capture_output=True, text=True, timeout=900)
    if PDF.exists():
        print(f"        {PDF.relative_to(ROOT)}")
    else:
        print("        PDF conversion FAILED:", out.stderr[:400])
    shutil.rmtree(WORK, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
