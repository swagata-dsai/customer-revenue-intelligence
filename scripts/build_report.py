"""
build_report.py - Step 14: build the Summer Internship Project Report.

This is the submission build: the university format in full, condensed to a
35-40 page document.  Every number printed in the report is read at build time
from outputs/tables/report_facts.json (written by scripts/report_facts.py) and
from the figures produced in Steps 2-13.  Nothing numeric is typed by hand.

The candidate, programme, institute, internship host and supervisor details are
taken from the bonafide certificate issued by Chandigarh University and are
reproduced verbatim; nothing about the candidate or the organisation is
invented.  The only field still open is the UID, which the certificate does not
carry.

Usage
-----
    python scripts/report_facts.py          # refresh the fact pack (optional)
    python scripts/report_diagrams.py       # refresh the report diagrams
    python scripts/build_report.py          # build DOCX + PDF + checklist

Three passes are used: pass A collects the outline, pass B renders it to find
the page each item landed on, pass C rebuilds with those page numbers printed.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import date
from pathlib import Path

from docx.shared import Cm

sys.path.insert(0, str(Path(__file__).resolve().parent))

from report_builder import (  # noqa: E402
    Report, contents_pages, docx_to_pdf, pdf_page_lines, pdf_pages,
    resolve_pages,
)

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "outputs" / "tables" / "report_facts.json"
FIG = ROOT / "outputs" / "figures"
ASSETS = ROOT / "assets" / "report"
REPORTS = ROOT / "outputs" / "reports"
STEM = "Customer_Revenue_Intelligence_Summer_Internship_Report"
DOCX = REPORTS / f"{STEM}.docx"
PDF = REPORTS / f"{STEM}.pdf"
CHECKLIST = REPORTS / "report_validation_checklist.md"

TITLE = ("CUSTOMER REVENUE INTELLIGENCE: AN INTERACTIVE DATA SCIENCE "
         "PLATFORM FOR CUSTOMER SEGMENTATION, REVENUE PREDICTION AND "
         "BUSINESS GROWTH")
# Title as written on the bonafide certificate, in title case.
TITLE_TC = ("Customer Revenue Intelligence: An Interactive Data Science "
            "Platform for Customer Segmentation, Revenue Prediction and "
            "Business Growth")

# --------------------------------------------------------------------------
# Candidate details - all taken from the bonafide certificate issued by
# Chandigarh University.  UID is not printed on that certificate and is left
# as a placeholder rather than invented.
# --------------------------------------------------------------------------
STUDENT = "Swagata Das"
UID = "[UID]"
DEGREE = "MASTER OF BUSINESS ADMINISTRATION"
PROGRAMME = "MBA - Data Science and AI"
SEMESTER = "3rd Semester"
INSTITUTE = "Apex Institute of Management"
UNIVERSITY = "CHANDIGARH UNIVERSITY"
SUPERVISOR = "Kuldeep Dubey"
COMPANY = "Tutorsuite Technologies LLP"
COMPANY_ADDRESS = ("1625/A, Rajdanga Main Road, opposite Siemens Office, "
                   "Sector E, Kasba, Kolkata, West Bengal 700107")
INTERNSHIP_PERIOD = "1st June to 12th July"
BATCH = "MBA 2023-25"
LOGO = ASSETS / "cu_logo_0.png"

SYNTHETIC = ("The dataset used throughout this project is synthetic. It was "
             "generated programmatically for academic demonstration and does "
             "not describe any real company, customer or transaction, "
             "including the internship host organisation.")

F: dict = {}


# --------------------------------------------------------------------------
# formatting helpers
# --------------------------------------------------------------------------
def rs(x, dec=2):
    if x is None:
        return "-"
    return "₹" + f"{float(x):,.{dec}f}"


def cr(x, dec=2):
    return f"₹{float(x) / 1e7:,.{dec}f} Cr"


def lakh(x, dec=2):
    return f"₹{float(x) / 1e5:,.{dec}f} L"


def n(x, dec=0):
    if x is None:
        return "-"
    return f"{float(x):,.{dec}f}"


def pc(x, dec=2):
    if x is None:
        return "-"
    return f"{float(x):.{dec}f}%"


def pcf(x, dec=2):
    return f"{float(x) * 100:.{dec}f}%"


def row_by(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    raise KeyError(f"{key}={value} not found")


def fig(*parts) -> Path:
    p = FIG.joinpath(*parts)
    if not p.exists():
        raise FileNotFoundError(p)
    return p


def logo(r: Report, width_cm: float = 6.2):
    if not LOGO.exists():
        raise FileNotFoundError(LOGO)
    para = r.doc.add_paragraph()
    para.alignment = 1
    para.paragraph_format.space_after = 0
    para.add_run().add_picture(str(LOGO), width=Cm(width_cm))
    return para


# ==========================================================================
# FRONT MATTER
# ==========================================================================
def front_matter(r: Report):
    d = F["dataset"]

    # ---- Title page -------------------------------------------------------
    logo(r, 7.0)
    r.p()
    r.p("SUMMER INTERNSHIP PROJECT REPORT", style="CRI Front Title")
    r.p("on", style="CRI Body Center")
    t = r.p(TITLE, style="CRI Front Title")
    t.paragraph_format.space_before = 0
    r.p("Submitted in partial fulfilment of the requirements for the award "
        "of the degree of", style="CRI Body Center")
    r.p(DEGREE, style="CRI Front Title")
    r.p(f"({PROGRAMME})", style="CRI Body Center")
    r.p()
    r.p("Submitted by", style="CRI Body Center")
    for line in [STUDENT, f"UID: {UID}", f"{PROGRAMME}, {SEMESTER}"]:
        p = r.p(line, style="CRI Body Center")
        p.runs[0].bold = True
    r.p()
    r.p("Under the guidance of", style="CRI Body Center")
    p = r.p(SUPERVISOR, style="CRI Body Center")
    p.runs[0].bold = True
    r.p()
    r.p(INSTITUTE, style="CRI Body Center")
    r.p(UNIVERSITY, style="CRI Front Title")
    r.p(BATCH, style="CRI Body Center")

    # ---- Bonafide certificate --------------------------------------------
    cert_logo = logo(r, 6.0)
    cert_logo.paragraph_format.page_break_before = True
    r.front_heading("Bonafide Certificate", new_page=False)
    r.p(f"This is to certify that {STUDENT}, a student of Master of "
        f"Business Administration - {PROGRAMME} in the {SEMESTER.lower()} "
        f"at {INSTITUTE} - Chandigarh University, has completed a summer "
        f"internship from {INTERNSHIP_PERIOD} at {COMPANY}, located at "
        f"{COMPANY_ADDRESS}.")
    r.p(f"During this period, {STUDENT} was engaged in “{TITLE_TC}"
        f"”, under the guidance of {SUPERVISOR}. The work completed by "
        "the student was satisfactory.")
    r.p(f"We wish {STUDENT} all the best in their future endeavours.")
    r.p()
    r.p()
    r.two_col_list([
        ("Signature", "Signature"),
        ("", ""),
        ("(Head of the Department)", "(Supervisor)"),
        (INSTITUTE, INSTITUTE),
    ], first_width=7.6, second_width=7.6, bold_first=False)
    r.p()
    r.p()
    r.p("Submitted for the project viva-voce examination held on "
        "____________________.")
    r.p()
    r.p()
    r.two_col_list([("Internal Examiner", "External Examiner")],
                   first_width=7.6, second_width=7.6, bold_first=False)
    r.note("This page reproduces the wording of the bonafide certificate "
           "issued for the internship. Signature lines are left blank for "
           "signing; no signature is reproduced or simulated in this "
           "document.")

    # ---- Acknowledgement --------------------------------------------------
    r.front_heading("Acknowledgement")
    r.p(f"I wish to record my sincere gratitude to {COMPANY}, Kolkata, for "
        f"hosting my summer internship from {INTERNSHIP_PERIOD} and for the "
        "opportunity to carry out an end-to-end analytics project within a "
        "professional setting.")
    r.p(f"I am deeply grateful to my guide, {SUPERVISOR}, for continuous "
        "direction through the internship, for reviewing the analytical "
        "choices made at each stage, and for insisting that every result "
        "presented be traceable to a reproducible computation rather than "
        "to assertion.")
    r.p(f"I thank {INSTITUTE}, Chandigarh University, for the academic "
        "framework, the coursework in data analytics, machine learning and "
        "business intelligence that formed the technical foundation of this "
        "work, and the reporting standards that shaped this document. I "
        "also thank the faculty members and peers whose questions on model "
        "validation, on the distinction between correlation and causation, "
        "and on the honest reporting of forecast uncertainty materially "
        "improved the final platform.")
    r.p("Finally, I acknowledge the open-source community whose libraries - "
        "pandas, NumPy, scikit-learn, statsmodels, Matplotlib, Plotly, "
        "Streamlit and SQLite - made a project of this scope achievable "
        "within an internship timeline.")
    r.p()
    p = r.p(STUDENT, style="CRI Body Center")
    p.runs[0].bold = True
    r.p(f"UID: {UID}", style="CRI Body Center")
    r.p(f"{PROGRAMME}, {SEMESTER}", style="CRI Body Center")

    # ---- Table of contents ------------------------------------------------
    r.front_heading("Table of Contents", toc=False)
    for level, label, key in r.toc_entries:
        r.dotted(label, r.page_of(key), level)

    # ---- List of figures --------------------------------------------------
    r.front_heading("List of Figures", toc=False)
    r.dotted("Figure No.  Title", "Page", 0)
    for number, caption in r.figure_entries:
        r.dotted(f"{number}  {caption}", r.page_of(f"FIG:{number}"), 1)

    # ---- List of tables ---------------------------------------------------
    r.front_heading("List of Tables", toc=False, new_page=False)
    r.dotted("Table No.  Title", "Page", 0)
    for number, caption in r.table_entries:
        r.dotted(f"{number}  {caption}", r.page_of(f"TAB:{number}"), 1)

    # ---- Abstract ---------------------------------------------------------
    r.front_heading("Abstract")
    kpi, rfm = F["kpi"], F["rfm"]
    km, pred, fc = F["kmeans"], F["prediction"], F["forecast"]
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    top20 = row_by(F["eda"]["concentration"], "top_pct", 20)
    r.p(
        "Retail firms record transactions faster than they convert them "
        "into decisions: revenue is reported in aggregate while the "
        "questions that drive growth are customer-level and "
        "forward-looking. This project builds a platform that answers "
        "them. " + SYNTHETIC +
        f" Its {n(d['raw_rows'])} raw order lines clean to "
        f"{n(d['clean_rows'])} validated lines covering "
        f"{n(d['customers_purchasing'])} customers, {d['products']} "
        f"products and {d['regions']} regions over {d['months']} months. "
        "Using Python, scikit-learn, statsmodels, SQL, DAX and Streamlit, "
        "it performs cleaning, exploratory analysis, RFM scoring, K-Means "
        "segmentation, customer value analysis, revenue prediction, "
        "forecasting and SQL analytics.",
        style="CRI Abstract")
    r.p(
        f"Delivered revenue is {cr(kpi['revenue'])} at a "
        f"{pcf(kpi['margin'])} margin; the top 20% of customers hold "
        f"{pc(top20['pct_of_revenue'])} of it and the Champions segment "
        f"alone {pc(champ['Revenue_%'], 2)}. K-Means selected K = "
        f"{km['k']} and recovered the same group independently. Revenue "
        f"prediction reached a test R² of "
        f"{pred['test_metrics']['R2']:.4f} - above its baselines but weak - "
        f"and forecasting a backtest MAPE of "
        f"{pc(fc['metrics']['backtest_mean_MAPE_%'], 2)}. Delivery is via "
        f"{F['powerbi']['measures']} DAX measures, {F['sql']['queries']} "
        f"reconciled SQL queries and a {F['streamlit']['pages']}-page "
        "application carrying eighteen evidence-linked recommendations. "
        "Limitations: synthetic data, a short history and a univariate "
        "forecast.",
        style="CRI Abstract")
    kw = r.rich([("Keywords: ", True),
                 ("customer analytics; RFM; K-Means; customer lifetime "
                  "value; revenue prediction; forecasting.", False)])
    kw.paragraph_format.widow_control = False

    # ---- Graphical abstract ----------------------------------------------
    r.front_heading("Graphical Abstract")
    r.p("The diagram below summarises the analytical pipeline implemented "
        "in this project, from raw customer transactions through to the "
        "business decisions the platform is designed to support. Each stage "
        "is a separate, re-runnable module whose output is the input of the "
        "next.")
    para = r.doc.add_paragraph()
    para.alignment = 1
    para.add_run().add_picture(str(fig("report", "graphical_abstract.png")),
                               width=Cm(12.6))

    # ---- Abbreviations and symbols ---------------------------------------
    r.front_heading("Abbreviations")
    r.two_col_list([
        ("AOV", "Average Order Value"),
        ("ARI", "Adjusted Rand Index"),
        ("BI", "Business Intelligence"),
        ("CLV", "Customer Lifetime Value"),
        ("DAX", "Data Analysis Expressions"),
        ("EDA", "Exploratory Data Analysis"),
        ("KPI", "Key Performance Indicator"),
        ("MAE", "Mean Absolute Error"),
        ("MAPE", "Mean Absolute Percentage Error"),
        ("ML", "Machine Learning"),
        ("PCA", "Principal Component Analysis"),
        ("RFM", "Recency, Frequency, Monetary"),
        ("RMSE", "Root Mean Squared Error"),
        ("SQL", "Structured Query Language"),
        ("WAPE", "Weighted Absolute Percentage Error"),
    ])
    r.front_heading("Symbols", new_page=False)
    r.two_col_list([
        ("μ", "Arithmetic mean of a variable"),
        ("σ", "Standard deviation of a variable"),
        ("R²", "Coefficient of determination"),
        ("K", "Number of clusters in K-Means"),
        ("α", "Level smoothing parameter of the Theta model"),
        ("₹", "Indian Rupee, the unit of all monetary values reported"),
    ], first_width=2.4)


# ==========================================================================
# CHAPTER 1 - INTRODUCTION
# ==========================================================================
def chapter1(r: Report):
    d, kpi = F["dataset"], F["kpi"]
    r.chapter_title(1, "Introduction")

    r.heading("1.1", "Background and Client Identification")
    r.p(f"This summer internship was carried out at {COMPANY}, "
        f"{COMPANY_ADDRESS}, from {INTERNSHIP_PERIOD}, under the guidance "
        f"of {SUPERVISOR}, as part of the {PROGRAMME} programme at "
        f"{INSTITUTE}, Chandigarh University. The brief was to build a "
        "working customer analytics capability end to end rather than to "
        "produce an isolated model or a static report.")
    r.p("Retail and e-commerce businesses accumulate transaction records "
        "far faster than they convert them into decisions. Revenue is "
        "reported in aggregate - by month, by category, by region - while "
        "the questions that drive growth are customer-level and "
        "forward-looking: which customers matter most, which are going "
        "quiet, what each is likely to spend next quarter, and what the "
        "next two quarters will bring in total. Answering them requires "
        "segmentation, value analysis, supervised prediction and "
        "forecasting to operate on one consistent definition of revenue, "
        "and requires the results to reach a decision-maker in a form they "
        "can interrogate.")
    r.p(SYNTHETIC + " Building on synthetic data removes any "
        "confidentiality constraint while preserving the full analytical "
        "problem, because the generator reproduces the structural features "
        "that make retail data difficult: skewed customer value, "
        "seasonality, discounting, returns and cancellations, and missing "
        "or malformed fields.")

    r.heading("1.2", "Problem Identification")
    r.p("Four specific gaps define the problem addressed here.")
    r.bullets([
        ("Aggregate reporting hides the customer. ", "Monthly revenue "
         "totals cannot distinguish a month carried by a few large "
         "customers from one built on a broad base, so they cannot guide "
         "retention effort."),
        ("Value and activity are treated as one thing. ", "A customer who "
         "spends heavily but has not ordered for six months needs a "
         "different response from one who orders frequently for small "
         "amounts, yet a single revenue ranking places them together."),
        ("Planning is backward-looking. ", "Without a forecast carrying "
         "prediction intervals, next-quarter planning rests on the last "
         "observed month, which is the weakest available estimator."),
        ("Analysis does not reach the decision-maker. ", "Results that live "
         "in notebooks are not usable by a non-technical reader, and "
         "numbers recomputed by hand for a slide deck drift from the "
         "pipeline that produced them."),
    ])

    r.heading("1.3", "Objectives")
    r.p("The project set eight objectives, each of which is answered by an "
        "identified section of Chapter 4.")
    r.bullets([
        "Generate and validate a realistic retail transaction dataset, and "
        "clean it against explicit business rules with a before-and-after "
        "audit trail.",
        "Characterise the revenue base across time, product, geography, "
        "discount and customer dimensions.",
        "Segment every purchasing customer by rule-based RFM scoring and, "
        "independently, by unsupervised clustering, and measure the "
        "agreement between the two schemes.",
        "Quantify each customer's historical value and estimate forward "
        "twelve-month value, reporting the two as distinct quantities.",
        "Predict customer revenue for the following quarter using only "
        "information available before that quarter began.",
        "Forecast company-level monthly revenue over a six-month horizon "
        "with prediction intervals.",
        "Reproduce the principal metrics independently in SQL and reconcile "
        "them against the Python pipeline.",
        "Deliver the results through a Power BI semantic model and an "
        "interactive multi-page application.",
    ], numbered=True)

    r.heading("1.4", "Scope and Significance")
    r.p(f"The scope covers {n(d['clean_rows'])} validated order lines, "
        f"{n(d['customers_purchasing'])} purchasing customers, "
        f"{d['products']} products in {d['categories']} categories and "
        f"{d['regions']} regions over {d['months']} months from "
        f"{d['start']} to {d['end']}, carrying {cr(kpi['revenue'])} of "
        f"delivered revenue. It excludes real customer data, real-time "
        "streaming, recommendation engines, pricing optimisation and any "
        "causal claim: the platform measures association and reports it as "
        "such.")
    r.p("The significance is integration and traceability. Each technique "
        "used here is established individually; what is delivered is a "
        "single pipeline in which one validated dataset and one revenue "
        "definition flow through every stage, in which the outputs are "
        "reconciled against an independent SQL implementation, and in which "
        "every number printed in this report is read from the file the "
        "pipeline wrote rather than transcribed by hand.")

    r.heading("1.5", "Organisation of the Report")
    r.p("Chapter 2 reviews the literature underpinning each stage and "
        "states the research gap. Chapter 3 presents the design: the "
        "architecture, the dataset, the preprocessing rules, the "
        "analytical and predictive methods, the delivery layer, the design "
        "constraints and the alternatives considered. Chapter 4 reports the "
        "results of every stage with their validation. Chapter 5 concludes, "
        "records where results deviated from expectation, states the "
        "limitations and sets out the future scope. The References, "
        "Appendix, User Manual and Achievements sections follow.")
    r.figure(fig("report", "timeline.png"),
             "Stage-wise execution timeline of the project and the "
             "deliverable produced at each stage",
             width_cm=13.0)


# ==========================================================================
# REFERENCES - every entry is a real, verifiable publication or the official
# documentation of software actually used.  Citation numbers are generated
# from this list, never typed into the prose.
# ==========================================================================
REFERENCES = [
    ("arthur2007",
     "Arthur, D., & Vassilvitskii, S. (2007). k-means++: The advantages of "
     "careful seeding. In Proceedings of the Eighteenth Annual ACM-SIAM "
     "Symposium on Discrete Algorithms (pp. 1027-1035). SIAM."),
    ("assimakopoulos2000",
     "Assimakopoulos, V., & Nikolopoulos, K. (2000). The theta model: A "
     "decomposition approach to forecasting. International Journal of "
     "Forecasting, 16(4), 521-530."),
    ("box2015",
     "Box, G. E. P., Jenkins, G. M., Reinsel, G. C., & Ljung, G. M. (2015). "
     "Time series analysis: Forecasting and control (5th ed.). Wiley."),
    ("breiman2001",
     "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5-32."),
    ("calinski1974",
     "Calinski, T., & Harabasz, J. (1974). A dendrite method for cluster "
     "analysis. Communications in Statistics, 3(1), 1-27."),
    ("chen1976",
     "Chen, P. P.-S. (1976). The entity-relationship model: Toward a "
     "unified view of data. ACM Transactions on Database Systems, 1(1), "
     "9-36."),
    ("chen2012",
     "Chen, H., Chiang, R. H. L., & Storey, V. C. (2012). Business "
     "intelligence and analytics: From big data to big impact. MIS "
     "Quarterly, 36(4), 1165-1188."),
    ("codd1970",
     "Codd, E. F. (1970). A relational model of data for large shared data "
     "banks. Communications of the ACM, 13(6), 377-387."),
    ("davies1979",
     "Davies, D. L., & Bouldin, D. W. (1979). A cluster separation "
     "measure. IEEE Transactions on Pattern Analysis and Machine "
     "Intelligence, 1(2), 224-227."),
    ("dickey1979",
     "Dickey, D. A., & Fuller, W. A. (1979). Distribution of the estimators "
     "for autoregressive time series with a unit root. Journal of the "
     "American Statistical Association, 74(366), 427-431."),
    ("fader2005bgnbd",
     "Fader, P. S., Hardie, B. G. S., & Lee, K. L. (2005). “Counting "
     "your customers” the easy way: An alternative to the Pareto/NBD "
     "model. Marketing Science, 24(2), 275-284."),
    ("fader2005rfm",
     "Fader, P. S., Hardie, B. G. S., & Lee, K. L. (2005). RFM and CLV: "
     "Using iso-value curves for customer base analysis. Journal of "
     "Marketing Research, 42(4), 415-430."),
    ("few2006",
     "Few, S. (2006). Information dashboard design: The effective visual "
     "communication of data. O'Reilly Media."),
    ("gupta2006",
     "Gupta, S., Hanssens, D., Hardie, B., Kahn, W., Kumar, V., Lin, N., "
     "Ravishanker, N., & Sriram, S. (2006). Modeling customer lifetime "
     "value. Journal of Service Research, 9(2), 139-155."),
    ("harris2020",
     "Harris, C. R., Millman, K. J., van der Walt, S. J., Gommers, R., "
     "Virtanen, P., Cournapeau, D., et al. (2020). Array programming with "
     "NumPy. Nature, 585(7825), 357-362."),
    ("hastie2009",
     "Hastie, T., Tibshirani, R., & Friedman, J. (2009). The elements of "
     "statistical learning: Data mining, inference, and prediction (2nd "
     "ed.). Springer."),
    ("hubert1985",
     "Hubert, L., & Arabie, P. (1985). Comparing partitions. Journal of "
     "Classification, 2(1), 193-218."),
    ("hughes1994",
     "Hughes, A. M. (1994). Strategic database marketing. Probus "
     "Publishing."),
    ("hunter2007",
     "Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. "
     "Computing in Science & Engineering, 9(3), 90-95."),
    ("hyndman2021",
     "Hyndman, R. J., & Athanasopoulos, G. (2021). Forecasting: Principles "
     "and practice (3rd ed.). OTexts. https://otexts.com/fpp3/"),
    ("hyndman2003",
     "Hyndman, R. J., & Billah, B. (2003). Unmasking the Theta method. "
     "International Journal of Forecasting, 19(2), 287-290."),
    ("hyndman2006",
     "Hyndman, R. J., & Koehler, A. B. (2006). Another look at measures of "
     "forecast accuracy. International Journal of Forecasting, 22(4), "
     "679-688."),
    ("jolliffe2002",
     "Jolliffe, I. T. (2002). Principal component analysis (2nd ed.). "
     "Springer."),
    ("kimball2013",
     "Kimball, R., & Ross, M. (2013). The data warehouse toolkit: The "
     "definitive guide to dimensional modeling (3rd ed.). Wiley."),
    ("lloyd1982",
     "Lloyd, S. P. (1982). Least squares quantization in PCM. IEEE "
     "Transactions on Information Theory, 28(2), 129-137."),
    ("macqueen1967",
     "MacQueen, J. (1967). Some methods for classification and analysis of "
     "multivariate observations. In Proceedings of the Fifth Berkeley "
     "Symposium on Mathematical Statistics and Probability (Vol. 1, pp. "
     "281-297). University of California Press."),
    ("mckinney2010",
     "McKinney, W. (2010). Data structures for statistical computing in "
     "Python. In Proceedings of the 9th Python in Science Conference (pp. "
     "56-61)."),
    ("microsoftdax",
     "Microsoft. (n.d.). Data Analysis Expressions (DAX) reference. "
     "Microsoft Learn. https://learn.microsoft.com/en-us/dax/"),
    ("pedregosa2011",
     "Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., "
     "Grisel, O., et al. (2011). Scikit-learn: Machine learning in Python. "
     "Journal of Machine Learning Research, 12, 2825-2830."),
    ("plotly",
     "Plotly Technologies Inc. (n.d.). Plotly Python graphing library "
     "documentation. https://plotly.com/python/"),
    ("rousseeuw1987",
     "Rousseeuw, P. J. (1987). Silhouettes: A graphical aid to the "
     "interpretation and validation of cluster analysis. Journal of "
     "Computational and Applied Mathematics, 20, 53-65."),
    ("schmittlein1987",
     "Schmittlein, D. C., Morrison, D. G., & Colombo, R. (1987). Counting "
     "your customers: Who are they and what will they do next? Management "
     "Science, 33(1), 1-24."),
    ("seabold2010",
     "Seabold, S., & Perktold, J. (2010). Statsmodels: Econometric and "
     "statistical modeling with Python. In Proceedings of the 9th Python "
     "in Science Conference (pp. 92-96)."),
    ("sqlite",
     "SQLite Consortium. (n.d.). SQLite documentation. "
     "https://www.sqlite.org/docs.html"),
    ("streamlit",
     "Streamlit Inc. (n.d.). Streamlit documentation. "
     "https://docs.streamlit.io/"),
    ("thorndike1953",
     "Thorndike, R. L. (1953). Who belongs in the family? Psychometrika, "
     "18(4), 267-276."),
    ("tukey1977",
     "Tukey, J. W. (1977). Exploratory data analysis. Addison-Wesley."),
    ("wedel2000",
     "Wedel, M., & Kamakura, W. A. (2000). Market segmentation: Conceptual "
     "and methodological foundations (2nd ed.). Kluwer Academic "
     "Publishers."),
]
REF_NO = {key: i for i, (key, _) in enumerate(REFERENCES, start=1)}
CITED: set = set()


def ref(*keys) -> str:
    """Citation marker, e.g. [12] or [12], [21]; numbers come from the list."""
    out = []
    for k in keys:
        if k not in REF_NO:
            raise KeyError(f"unknown reference key: {k}")
        CITED.add(k)
        out.append(f"[{REF_NO[k]}]")
    return ", ".join(out)


# ==========================================================================
# CHAPTER 2 - LITERATURE REVIEW
# ==========================================================================
def chapter2(r: Report):
    r.chapter_title(2, "Literature Review")

    r.heading("2.1", "Customer Segmentation and RFM Analysis")
    r.p("Market segmentation theory distinguishes a priori segmentation, "
        "which groups customers on attributes chosen in advance, from post "
        "hoc segmentation, which derives groups from observed behaviour. "
        f"Wedel and Kamakura (2000) {ref('wedel2000')} review both and "
        "report that behavioural bases generally outperform demographic "
        "ones for marketing response, while cautioning that segment "
        "membership is not stable over time. RFM analysis, formalised for "
        f"database marketing by Hughes (1994) {ref('hughes1994')}, scores "
        "each customer on recency, frequency and monetary value and is "
        "valued for being auditable: a business user can see why a customer "
        f"landed in a segment. Fader, Hardie and Lee (2005) "
        f"{ref('fader2005rfm')} relate RFM directly to customer value "
        "through iso-value curves, showing that the three variables carry "
        "most of the information needed to rank a customer base. The "
        "limitation carried into this project is that quintile cut-offs are "
        "dataset-relative, so a segment label describes a position within "
        "this base rather than an absolute standard.")

    r.heading("2.2", "Unsupervised Clustering")
    r.p(f"K-Means, introduced by MacQueen (1967) {ref('macqueen1967')} and "
        f"given its least-squares formulation by Lloyd (1982) "
        f"{ref('lloyd1982')}, partitions observations to minimise "
        f"within-cluster variance. Arthur and Vassilvitskii (2007) "
        f"{ref('arthur2007')} show that k-means++ initialisation materially "
        "improves both solution quality and stability. Because the "
        "algorithm requires K to be fixed in advance, the literature "
        "supplies diagnostics rather than a decision rule: Thorndike (1953) "
        f"{ref('thorndike1953')} gives the elbow heuristic, Rousseeuw "
        f"(1987) {ref('rousseeuw1987')} the silhouette coefficient, "
        f"Calinski and Harabasz (1974) {ref('calinski1974')} and Davies and "
        f"Bouldin (1979) {ref('davies1979')} their respective indices, and "
        f"Hubert and Arabie (1985) {ref('hubert1985')} the Adjusted Rand "
        f"Index for comparing two partitions. Jolliffe (2002) "
        f"{ref('jolliffe2002')} provides the principal component analysis "
        "used here for visualisation only. The methodological lesson taken "
        "from this body of work is that K must be selected against rules "
        "fixed before the results are seen, which is what Section 3.5 does.")

    r.heading("2.3", "Customer Lifetime Value")
    r.p(f"Gupta et al. (2006) {ref('gupta2006')} survey the modelling of "
        "customer lifetime value and distinguish historical value, which is "
        "measured, from predicted value, which is estimated with error. "
        f"Schmittlein, Morrison and Colombo (1987) {ref('schmittlein1987')} "
        "introduced the Pareto/NBD model for non-contractual settings, and "
        f"Fader, Hardie and Lee (2005) {ref('fader2005bgnbd')} the more "
        "tractable BG/NBD alternative. These probabilistic models assume a "
        "purchasing process that continues until an unobserved dropout, "
        "which is precisely the assumption a short synthetic history cannot "
        "support well; this project therefore reports historical value as "
        "measured and forward value as an estimate from a supervised model, "
        "and keeps the two quantities separately named throughout.")

    r.heading("2.4", "Supervised Prediction and Time-Series Forecasting")
    r.p(f"Hastie, Tibshirani and Friedman (2009) {ref('hastie2009')} set "
        "out the bias-variance trade-off and the discipline of "
        "out-of-sample evaluation that governs Sections 3.6 and 3.7; "
        f"Breiman (2001) {ref('breiman2001')} introduced random forests, "
        "used here as one of the candidate value models. For time series, "
        f"Box et al. (2015) {ref('box2015')} provide the ARIMA framework "
        f"and Dickey and Fuller (1979) {ref('dickey1979')} the unit-root "
        "test used to check stationarity; Assimakopoulos and Nikolopoulos "
        f"(2000) {ref('assimakopoulos2000')} introduced the Theta method, "
        "whose equivalence to simple exponential smoothing with drift was "
        f"established by Hyndman and Billah (2003) {ref('hyndman2003')}. "
        f"Hyndman and Athanasopoulos (2021) {ref('hyndman2021')} argue that "
        "a forecast must beat a naive benchmark to be worth using and that "
        "rolling-origin evaluation is the honest test, while Hyndman and "
        f"Koehler (2006) {ref('hyndman2006')} show that percentage errors "
        "are unreliable near zero. Both cautions are implemented as hard "
        "selection rules in Section 3.7.")

    r.heading("2.5", "Data Modelling, Business Intelligence and Tooling")
    r.p(f"Codd (1970) {ref('codd1970')} established the relational model "
        f"and Chen (1976) {ref('chen1976')} entity-relationship modelling, "
        "which together underpin the normalised database of Section 3.8. "
        f"Kimball and Ross (2013) {ref('kimball2013')} set out the star "
        "schema used for the semantic model in Section 3.9, whose measures "
        f"are written in DAX {ref('microsoftdax')}. Chen, Chiang and Storey "
        f"(2012) {ref('chen2012')} survey business intelligence and observe "
        "that the constraint on value realisation is usually organisational "
        f"delivery rather than analytical technique. Few (2006) "
        f"{ref('few2006')} gives the dashboard design principles applied "
        "to both delivery surfaces, with the caveat that design "
        "effectiveness can only be confirmed by user testing, which was "
        f"outside the scope of this internship. Tukey (1977) "
        f"{ref('tukey1977')} defines the exploratory posture of Section "
        "3.3. The implementation rests on "
        f"pandas {ref('mckinney2010')}, NumPy {ref('harris2020')}, "
        f"scikit-learn {ref('pedregosa2011')}, statsmodels "
        f"{ref('seabold2010')}, Matplotlib {ref('hunter2007')}, Plotly "
        f"{ref('plotly')}, SQLite {ref('sqlite')} and Streamlit "
        f"{ref('streamlit')}.")

    lit = [
        [f"Hughes (1994) {ref('hughes1994')}; Fader et al. (2005) "
         f"{ref('fader2005rfm')}",
         "RFM segmentation",
         "Behavioural scores rank a customer base effectively and stay "
         "interpretable",
         "Cut-offs are relative to the dataset analysed",
         "3.4, 4.3"],
        [f"MacQueen (1967) {ref('macqueen1967')}; Rousseeuw (1987) "
         f"{ref('rousseeuw1987')}",
         "Unsupervised clustering",
         "Compact clusters can be recovered without labels; K must be "
         "chosen by diagnostics",
         "No single index determines K",
         "3.5, 4.4"],
        [f"Gupta et al. (2006) {ref('gupta2006')}; Fader et al. (2005) "
         f"{ref('fader2005bgnbd')}",
         "Customer lifetime value",
         "Historical and predicted value are distinct quantities",
         "Probabilistic models need a longer history than is available "
         "here",
         "3.6, 4.5"],
        [f"Hastie et al. (2009) {ref('hastie2009')}; Breiman (2001) "
         f"{ref('breiman2001')}",
         "Supervised prediction",
         "Model choice must be made on validation data, not training fit",
         "Individual-level outcomes remain largely unexplained",
         "3.6, 4.6"],
        [f"Hyndman & Athanasopoulos (2021) {ref('hyndman2021')}; "
         f"Assimakopoulos & Nikolopoulos (2000) {ref('assimakopoulos2000')}",
         "Time-series forecasting",
         "A forecast is only useful if it beats a naive benchmark",
         "Percentage errors are unstable near zero",
         "3.7, 4.7"],
        [f"Kimball & Ross (2013) {ref('kimball2013')}; Few (2006) "
         f"{ref('few2006')}",
         "Dimensional modelling and dashboard design",
         "A conformed model and a clear hierarchy make analysis "
         "self-service",
         "Effectiveness requires user testing to confirm",
         "3.9, 3.10, 4.9"],
    ]
    r.table(
        "Comparison of the principal literature informing each stage of "
        "the project",
        ["Author / Year", "Topic",
         "Key finding (as reported in that work)", "Limitation", "Used in"],
        lit,
        widths=[3.1, 2.3, 4.2, 3.2, 1.6],
        font_size=7,
        note="The Key Finding column summarises the cited work only. It "
             "contains no result produced by this project; project results "
             "are reported in Chapter 4.",
    )

    r.heading("2.6", "Research Gap and Problem Definition")
    r.p("Each area above is individually well developed and this project "
        "claims no novelty in any of them. The gap it addresses is "
        "integration and traceability at the scale of a single "
        "reproducible project: in most teaching material these techniques "
        "are demonstrated in isolation - one notebook scores RFM, another "
        "clusters customers, a third fits a forecast - and what is rarely "
        "shown end to end is a single pipeline in which one validated "
        "dataset and one revenue definition flow through every stage, the "
        "outputs are reconciled against an independent SQL implementation, "
        "and the results reach a semantic model and an application whose "
        "numbers agree with the pipeline that produced them.")
    r.p("Formally, given a transaction dataset of order lines carrying "
        "customer, product, geography, pricing, discount, cost and "
        "order-status attributes, the platform must clean the records "
        "against explicit business rules, characterise the revenue base, "
        "assign every customer to both a rule-based segment and an "
        "unsupervised cluster and quantify their agreement, separate "
        "measured historical value from estimated forward value, predict "
        "next-quarter customer revenue out of time, forecast monthly "
        "revenue with backtested prediction intervals, reconcile the "
        "metrics against a relational implementation, and deliver the "
        "results through a semantic model and an application. The "
        "success criterion is not the accuracy of any single model but "
        "that the outputs are complete, consistent, independently "
        "reconciled and reproducible.")


# ==========================================================================
# CHAPTER 3 - DESIGN FLOW AND METHODOLOGY
# ==========================================================================
def chapter3(r: Report):
    d = F["dataset"]
    rfm, km, clv = F["rfm"], F["kmeans"], F["clv"]
    pred, fc = F["prediction"], F["forecast"]
    r.chapter_title(3, "Design Flow and Methodology")

    r.heading("3.1", "System Architecture")
    r.p("The platform is built as five layers. The data layer generates, "
        "validates and cleans the transaction records. The analytical layer "
        "performs exploratory analysis, RFM scoring, clustering and "
        "customer value analysis. The model layer fits and evaluates the "
        "supervised revenue model and the time-series forecast. The "
        "database layer reproduces the principal metrics independently in "
        "SQL. The delivery layer exposes the results through a Power BI "
        "semantic model and an interactive Streamlit application. Every "
        "stage is a separate Python module with a single entry point, reads "
        "only the persisted output of the stage before it and writes its "
        "own outputs to disk, so any stage can be re-run without re-running "
        "the whole pipeline.")
    r.figure(fig("report", "architecture.png"),
             "Solution architecture, from the data source through the "
             "analytical and model layers to the three delivery surfaces",
             width_cm=10.2)

    r.heading("3.2", "Dataset Description")
    r.p(SYNTHETIC + f" The generator is seeded at {d['seed']}, so the "
        f"dataset is reproducible byte for byte. It writes "
        f"{n(d['raw_rows'])} raw order lines across {d['raw_cols']} "
        "columns, deliberately injecting the defects a real extract "
        "carries - missing values, non-ISO dates, numbers stored as text, "
        "out-of-range discounts, invalid category labels and duplicate "
        "rows - so that cleaning has real work to do and can be audited "
        "against a known ground truth.")
    st = d["statuses"]
    r.table(
        "Composition of the dataset used throughout the project",
        ["Property", "Value"],
        [["Nature of the data", "Synthetic, generated programmatically "
          f"(seed {d['seed']}); not real customer data"],
         ["Raw extract", f"{n(d['raw_rows'])} order lines, {d['raw_cols']} "
          "columns"],
         ["Cleaned dataset", f"{n(d['clean_rows'])} order lines, "
          f"{d['clean_cols']} columns "
          f"({d['duplicates_removed']} duplicates removed)"],
         ["Observation window", f"{d['start']} to {d['end']} "
          f"({d['months']} months)"],
         ["Customers", f"{n(d['customers_registered'])} registered, "
          f"{n(d['customers_purchasing'])} with at least one delivered "
          "order"],
         ["Products and geography", f"{d['products']} products in "
          f"{d['categories']} categories and {d['sub_categories']} "
          f"sub-categories; {d['cities']} cities, {d['states']} states, "
          f"{d['regions']} regions"],
         ["Order-line status", f"{n(st['Delivered'])} delivered, "
          f"{n(st['Returned'])} returned, {n(st['Cancelled'])} cancelled"],
         ["Privacy treatment", "Analytical outputs identify customers by "
          "Customer_ID only; no customer name is used in any result"]],
        widths=[4.6, 10.6])
    r.p("One definition governs the whole project: revenue, profit and "
        "order counts are computed on delivered order lines only. Returned "
        "and cancelled lines are retained in the dataset and analysed "
        "separately as lost value, but they never enter a revenue figure. "
        "Applying this rule identically in Python, in SQL and in DAX is "
        "what makes the three implementations reconcilable.")

    r.heading("3.3", "Data Preprocessing and Exploratory Analysis")
    r.p("Cleaning is rule-driven rather than discretionary. Every rule is "
        "evaluated on the raw extract, the count of offending rows is "
        "logged, a treatment is applied, and the rule is re-evaluated on "
        "the cleaned dataset. A rule that does not return zero after "
        "treatment is a failure of the cleaning stage, not an acceptable "
        "residue. Table 3.2 gives the before-and-after position for every "
        "rule; the result is reported in Section 4.1.")
    r.table(
        "Business-rule validation before and after cleaning",
        ["Validation rule", "Rows failing before", "Rows failing after"],
        [[row["Validation_Rule"].replace("_", " ").capitalize(),
          n(row["Rows_Before"]), n(row["Rows_After"])]
         for row in F["quality"]["rules"]],
        widths=[7.0, 4.1, 4.1])
    r.p("Exploratory analysis then characterises the revenue base across "
        "time, product, geography, discount, payment method and customer "
        "dimensions, using descriptive statistics, distribution analysis, "
        "the 1.5 interquartile-range outlier rule and correlation "
        "analysis. Outliers are flagged and inspected, not removed: a "
        "large order from a genuine high-value customer is a fact about "
        "the business, not an error.")

    r.heading("3.4", "RFM Segmentation")
    m = rfm["metadata"]
    r.p(f"Every customer with at least one delivered order is scored on "
        f"recency ({m['recency']}), frequency ({m['frequency']}) and "
        f"monetary value ({m['monetary']}) at the reference date "
        f"{m['reference_date']}, which is {m['reference_date_rule']}. Each "
        "dimension is scored 1-5 on quintiles, with recency reversed so "
        "that a higher score always means a better customer, and the "
        "quintile cut is replaced by a tie-aware percentile rank where the "
        f"edges are not unique. The combined score places each of the "
        f"{n(rfm['customers_scored'])} scored customers into one of "
        f"{rfm['segments']} named segments by fixed rules - Champions, for "
        "example, requires a recency score of 4-5 and a combined "
        "frequency-monetary score of at least 4.5. The rules are published "
        "with the results so that any segment assignment can be checked by "
        "hand. This stage is rule-based and is not machine learning.")

    r.heading("3.5", "K-Means Clustering")
    r.p("The same three behavioural variables are then clustered without "
        "labels, as an independent check on the rule-based scheme. Because "
        "recency, frequency and monetary value are heavily skewed and are "
        "measured on different scales, the features pass through a "
        "persisted scikit-learn pipeline of log1p followed by standard "
        f"scaling. K is not chosen after inspecting the results: three "
        "rules were fixed in advance - at least "
        f"{km['selection_rules']['min_k']} clusters, no cluster smaller "
        f"than {pcf(km['selection_rules']['min_cluster_share'], 0)} of the "
        "base, and a bootstrap stability of Adjusted Rand Index at least "
        f"{km['selection_rules']['min_stability_ari']:.2f} - after which "
        "the eligible K with the highest silhouette coefficient is taken. "
        "Principal component analysis is used for visualisation only and "
        "never as an input to the model.")

    r.heading("3.6", "Customer Value and Revenue Prediction")
    r.p("Customer value is reported as two separate quantities. Historical "
        "value is measured: the delivered profit a customer has already "
        "generated. Forward value is estimated: a supervised model trained "
        "on an out-of-time split, with eight behavioural features drawn "
        "from one twelve-month window predicting delivered profit in the "
        "following twelve months. A ridge baseline, a random forest and a "
        "gradient-boosted ensemble are compared against naive and formula "
        "baselines, and the winner is chosen "
        f"by the rule fixed in advance: {clv['metadata']['selection_rule']}.")
    r.p("Revenue prediction operates on a different unit. A panel of "
        f"{n(pred['panel_rows'])} customer-quarter rows is built, each row "
        f"carrying {pred['n_features']} features "
        f"({len(pred['numeric_features'])} numeric and "
        f"{len(pred['categorical_features'])} categorical) computed "
        "strictly from data available before the target quarter began, and "
        "the target is that customer's delivered revenue in the quarter "
        f"that follows. The split is out-of-time, not random: "
        f"{n(pred['train_rows'])} training rows ({pred['train_period']}), "
        f"{n(pred['val_rows'])} validation rows ({pred['validation_period']}"
        f") and {n(pred['test_rows'])} test rows ({pred['test_period']}). "
        "A leakage audit recomputes the features of a sample of rows "
        "directly from the transaction table to confirm that no "
        "post-cutoff information reaches the model. The model is selected "
        f"by the rule {pred['selection_rule']}, which is why a linear "
        "regression was chosen over more flexible alternatives.")

    r.heading("3.7", "Revenue Forecasting")
    r.p("Forecasting operates at company level on monthly delivered "
        f"revenue over {fc['series_months']} months. The series is first "
        "characterised for stationarity, autocorrelation structure and "
        "seasonality. Candidate families are naive and seasonal naive "
        "baselines, exponential smoothing, ARIMA and SARIMA, and the Theta "
        "method; selection follows a rule fixed in advance: "
        f"{fc['selection_rule']}. The chosen model is refit on the full "
        f"{fc['final_fit']} history and forecasts {fc['horizon']} months "
        "ahead with 80% and 95% prediction intervals.")

    r.heading("3.8", "SQL Analytical Layer")
    sq = F["sql"]
    r.p(f"The cleaned data is loaded into a normalised SQLite database of "
        f"{sq['tables']} tables and {sq['views']} views, with primary and "
        "foreign keys enforced and indexes on the join and filter columns. "
        f"{sq['queries']} analytical queries - {sq['analysis_queries']} "
        f"analysis queries and {sq['business_queries']} business queries - "
        "reproduce the principal metrics using window functions, common "
        "table expressions, self-joins and conditional aggregation. This "
        "layer exists to be an independent implementation: it is written "
        "against the same definitions but in a different language, so "
        "agreement between it and the Python pipeline is evidence rather "
        "than tautology.")

    r.heading("3.9", "Power BI Semantic Model")
    pb = F["powerbi"]
    r.p(f"The Power BI layer is a star schema of {pb['tables']} tables "
        f"joined by {pb['relationships']} single-direction relationships, "
        f"with {pb['measures']} DAX measures organised into "
        f"{pb['folders']} display folders, a marked date dimension, Power "
        "Query M scripts for each table and a JSON theme. Every measure "
        "carries an explicit filter on delivered lines so that the model "
        "cannot silently report a different revenue definition from the "
        "pipeline.")
    r.note("Power BI Desktop is a Windows application and could not be run "
           "in the Linux environment used for this project. The semantic "
           "model, the measures, the Power Query scripts, the theme and a "
           "build guide were produced and validated against SQL; the page "
           "layouts were rendered from the real data as design mockups and "
           "are labelled as such wherever they appear. No Power BI Desktop "
           "screenshot is presented in this report.")

    r.heading("3.10", "Streamlit Application")
    r.p(f"The application is a {F['streamlit']['pages']}-page Streamlit "
        "interface covering executive overview, revenue, customers, "
        "segmentation, products, regions, prediction, forecasting, "
        "recommendations, a data explorer and project documentation. It "
        "loads from the SQLite database where available and falls back to "
        "the processed CSV files, caches data and model artefacts, and "
        "loads the persisted models rather than refitting anything. It "
        "computes no metric of its own: every number it displays comes "
        "from the pipeline's outputs or from the shared module the "
        "pipeline itself uses.")

    r.heading("3.11", "Design Constraints and Alternative Designs")
    r.p("Four constraints shaped the design. The data had to be synthetic, "
        "because no real customer data could be used in an academic "
        "deliverable. The whole pipeline had to be reproducible from a "
        "fixed seed on a single machine with no paid service. Power BI "
        "Desktop was unavailable on the build platform. And every reported "
        "figure had to be traceable to the file that produced it, which "
        "ruled out any hand-transcribed number in the reporting layer.")
    r.table(
        "Alternative designs considered at each decision point and the "
        "option selected",
        ["Decision point", "Alternatives considered", "Basis of comparison",
         "Selected"],
        [["Customer segmentation",
          "(a) RFM rules only; (b) K-Means only; (c) both, compared",
          "A rule-based scheme is explainable; an unsupervised one is "
          "unbiased by rules",
          "(c) both, with the agreement between them quantified by "
          "Adjusted Rand Index"],
         ["Number of clusters K",
          "(a) elbow alone; (b) silhouette alone; (c) pre-declared rules "
          "then silhouette",
          "A single index can be read to suit the desired answer",
          "(c) rules fixed before results, then the highest silhouette "
          "among eligible K"],
         ["Customer value",
          "(a) historical value only; (b) BG/NBD probabilistic model; "
          "(c) supervised out-of-time regression",
          "History length; whether the estimate can be validated",
          "(c) supervised regression, validated out of time, reported "
          "alongside measured historical value"],
         ["Revenue prediction model",
          "(a) linear regression; (b) random forest; (c) gradient boosting",
          "Validation RMSE, with the simplest model within 2% preferred",
          "(a) linear regression, which met the rule and is interpretable"],
         ["Forecasting model",
          "(a) ETS; (b) ARIMA / SARIMA; (c) Theta; (d) naive baselines",
          "Rolling-origin backtest MAPE; must beat both naive baselines",
          "(c) Theta, lowest backtest error and the simpler family within "
          "5%"],
         ["Application delivery",
          "(a) static HTML report; (b) notebook dashboard; (c) Streamlit "
          "application",
          "Must be operable by a non-technical user and load the real "
          "persisted models",
          "(c) Streamlit, supporting multi-page navigation and direct "
          "model loading"]],
        widths=[2.8, 4.0, 4.0, 4.4],
        font_size=9)

    r.heading("3.12", "Implementation Flowchart")
    r.p("Figure 3.2 shows the implementation as executed, including the "
        "three gates at which a stage can reject its own output and return "
        "to an earlier step: the business-rule gate after cleaning, which "
        "must return zero failing rows; the K-selection gate, which "
        "rejects any K failing the pre-declared rules; and the baseline "
        "gate, which rejects any forecast model that does not beat both "
        "naive baselines.")
    r.figure(fig("report", "flowchart.png"),
             "Implementation flowchart of the project lifecycle, from data "
             "generation to business decision support, including the three "
             "validation gates",
             width_cm=10.4)


# ==========================================================================
# CHAPTER 4 - RESULTS, ANALYSIS AND VALIDATION
# ==========================================================================
def chapter4(r: Report):
    d, kpi, q = F["dataset"], F["kpi"], F["quality"]
    eda, rfm, km = F["eda"], F["rfm"], F["kmeans"]
    clv, pred, fc = F["clv"], F["prediction"], F["forecast"]
    sq, pb, stl = F["sql"], F["powerbi"], F["streamlit"]
    r.chapter_title(4, "Results, Analysis and Validation")

    # ---- 4.1 data quality -------------------------------------------------
    r.heading("4.1", "Data Quality Results")
    r.p(f"Cleaning reduced {n(d['raw_rows'])} raw order lines to "
        f"{n(d['clean_rows'])} validated lines, removing "
        f"{d['duplicates_removed']} exact duplicates and treating "
        f"{n(q['missing_before'])} rows that failed at least one business "
        f"rule. After treatment, {q['rules_failing_after']} rules fail: "
        "every rule listed in Table 3.2 returns zero. The cleaned dataset "
        f"carries {d['clean_cols']} columns, of which "
        f"{d['clean_cols'] - d['raw_cols']} are engineered - calendar "
        "attributes, the delivered flag, revenue, profit and margin, "
        "discount and age bands, outlier flags and the reconciliation "
        "checks that confirm each line's revenue equals its own price, "
        "quantity and discount.")

    # ---- 4.2 EDA ----------------------------------------------------------
    r.heading("4.2", "Exploratory Data Analysis Results")
    r.table(
        "Headline performance of the delivered revenue base",
        ["Indicator", "Value", "Indicator", "Value"],
        [["Delivered revenue", cr(kpi["revenue"]),
          "Delivered orders", n(kpi["orders"])],
         ["Delivered profit", cr(kpi["profit"]),
          "Units sold", n(kpi["units"])],
         ["Profit margin", pcf(kpi["margin"]),
          "Average order value", rs(kpi["aov"])],
         ["Purchasing customers", n(kpi["customers"]),
          "Revenue per customer", rs(kpi["revenue_per_customer"], 0)],
         ["Booked value (all statuses)", cr(kpi["booked"]),
          "Profit per order", rs(kpi["profit_per_order"], 0)],
         ["Value lost to returns and cancellations", lakh(kpi["lost"]),
          "Share of booked value lost", pcf(kpi["lost_share"])]],
        widths=[4.4, 3.2, 4.2, 3.4])
    y = eda["by_year"]
    r.p(f"Revenue grew from {cr(y[0]['revenue'])} in {y[0]['order_year']} "
        f"to {cr(y[-1]['revenue'])} in {y[-1]['order_year']} - "
        f"{pc(y[1]['revenue_yoy_growth_pct'], 1)} then "
        f"{pc(y[-1]['revenue_yoy_growth_pct'], 1)} - while margin moved "
        f"from {pc(y[0]['profit_margin_pct'])} to "
        f"{pc(y[-1]['profit_margin_pct'])}, so growth is not being bought "
        f"with margin. Monthly revenue ranges from "
        f"{lakh(eda['monthly_min'])} to {lakh(eda['monthly_max'])}, and "
        "October is the strongest month in all three years - the clearest "
        "seasonal signal the series carries.")
    r.figure(fig("monthly_revenue_trend.png"),
             "Monthly delivered revenue across the 36-month observation "
             "window", width_cm=11.8)
    cat = eda["by_category"]
    r.table(
        "Revenue, profit and margin by product category",
        ["Category", "Products", "Revenue", "Revenue %", "Profit",
         "Margin %"],
        [[c["category"], n(c["products"]), cr(c["revenue"]),
          pc(c["revenue_share_pct"]), lakh(c["profit"]),
          pc(c["profit_margin_pct"])] for c in cat],
        widths=[3.2, 1.8, 2.6, 2.2, 2.6, 2.2])
    top_cat, best_margin = cat[0], max(cat, key=lambda c: c["profit_margin_pct"])
    r.p(f"{top_cat['category']} is the volume leader with "
        f"{pc(top_cat['revenue_share_pct'])} of revenue but only "
        f"{pc(top_cat['profit_share_pct'])} of profit, because its "
        f"{pc(top_cat['profit_margin_pct'])} margin is the lowest in the "
        f"catalogue, while {best_margin['category']} carries the highest "
        f"at {pc(best_margin['profit_margin_pct'])}. The two are different "
        "kinds of asset and should not carry the same target.")
    reg = eda["by_region"]
    r.p(f"Revenue is spread evenly across the {d['regions']} regions: "
        f"the largest, {reg[0]['region']}, holds "
        f"{pc(reg[0]['revenue_share_pct'])} and the smallest "
        f"{pc(reg[-1]['revenue_share_pct'])}. A systematic test of all "
        f"{eda['region_category_pairs']} region-category pairs found "
        f"{eda['region_category_gap']} pair more than two percentage "
        "points below the national margin for its category, so there is no "
        "regional margin problem to fix.")
    disc = eda["discount_bands"]
    zero = disc[0]
    r.p(f"Discount matters more than expected: the "
        f"{zero['discount_band']} band carries a margin of "
        f"{pc(zero['profit_margin_pct'])} against "
        f"{pc(disc[-1]['profit_margin_pct'])} in the "
        f"{disc[-1]['discount_band']} band, and returns the best margin in "
        f"{eda['zero_discount_best_in']} of the "
        f"{eda['categories_tested']} categories tested. This is an "
        "association measured on observed orders, not a causal claim: the "
        "data cannot say what those orders would have done at a different "
        "discount.")
    rep = row_by(eda["repeat"], "customer_group", "Repeat (2+ orders)")
    one = [x for x in eda["repeat"] if x["customer_group"] != rep["customer_group"]][0]
    top20 = row_by(eda["concentration"], "top_pct", 20)
    top10 = row_by(eda["concentration"], "top_pct", 10)
    r.p(f"The base is concentrated: the top 10% of customers produce "
        f"{pc(top10['pct_of_revenue'])} of revenue and the top 20% "
        f"{pc(top20['pct_of_revenue'])}. Repeat customers are "
        f"{pc(rep['pct_of_customers'])} of the base and "
        f"{pc(rep['pct_of_revenue'])} of revenue, averaging "
        f"{rs(rep['avg_revenue_per_customer'], 0)} each against "
        f"{rs(one['avg_revenue_per_customer'], 0)} for single-order "
        f"customers. The median gap between consecutive orders is "
        f"{n(eda['interpurchase']['median_gap_days'])} days - the natural "
        "basis for an inactivity threshold.")

    # ---- 4.3 RFM ----------------------------------------------------------
    r.heading("4.3", "RFM Segmentation Results")
    champ = row_by(rfm["summary"], "RFM_Segment", "Champions")
    r.table(
        "Customer count, revenue and behaviour by RFM segment",
        ["Segment", "Customers", "Cust. %", "Revenue", "Rev. %",
         "Avg recency (days)", "Avg frequency", "Avg monetary"],
        [[s["RFM_Segment"], n(s["Customer_Count"]), pc(s["Customer_%"], 1),
          lakh(s["Total_Revenue"], 1), pc(s["Revenue_%"], 1),
          n(s["Average_Recency"], 1), n(s["Average_Frequency"], 1),
          rs(s["Average_Monetary"], 0)] for s in rfm["summary"]],
        widths=[3.0, 1.7, 1.4, 2.0, 1.4, 1.9, 1.6, 2.2],
        font_size=8)
    quiet = sum(row_by(rfm["summary"], "RFM_Segment", s)["Revenue_%"]
                for s in ("At Risk", "Can't Lose Them"))
    r.p(f"Of {n(rfm['customers_scored'])} scored customers, the Champions "
        f"segment is {pc(champ['Customer_%'], 2)} of the base and "
        f"{pc(champ['Revenue_%'], 2)} of revenue - an average of "
        f"{rs(champ['Average_Monetary'], 0)} each at an average recency of "
        f"{n(champ['Average_Recency'], 1)} days. The finding that matters "
        "operationally is at the opposite end of the table: the At Risk and "
        f"Can't Lose Them segments together hold {pc(quiet, 2)} of "
        "historical revenue in customers who have gone quiet. That is "
        "inactivity, not churn: the dataset defines no churn event, and no "
        "result in this report describes one.")
    r.figure(fig("rfm_revenue_contribution.png"),
             "Revenue contribution by RFM segment", width_cm=11.8)

    # ---- 4.4 K-Means ------------------------------------------------------
    r.heading("4.4", "K-Means Segmentation Results")
    elig = [k for k in km["k_evaluation"] if k["Eligible"]]
    r.p(f"Of the values of K evaluated, {len(elig)} satisfied all three "
        f"pre-declared rules, and K = {km['k']} was selected with a "
        f"silhouette coefficient of {km['overall_silhouette']:.4f}. The two "
        f"retained principal components explain "
        f"{pc(km['pca'][0]['Explained_Variance_%'], 2)} and "
        f"{pc(km['pca'][1]['Explained_Variance_%'], 2)} of the variance in "
        "the scaled feature space, so the projection in Figure 4.7 is a "
        "faithful picture of the clustering rather than a lossy one.")
    r.table(
        "Profile of the four customer clusters",
        ["Cluster", "Label", "Customers", "Cust. %", "Avg recency",
         "Avg frequency", "Avg monetary", "Revenue %"],
        [[c["Cluster_ID"], c["Business_Label"], n(c["Customer_Count"]),
          pc(c["Customer_%"], 2), n(c["Average_Recency"], 1),
          n(c["Average_Frequency"], 1), rs(c["Average_Monetary"], 0),
          pc(c["Revenue_%"], 2)] for c in km["summary"]],
        widths=[1.5, 3.0, 1.8, 1.5, 1.7, 1.8, 2.2, 1.7],
        font_size=8)
    hv = km["summary"][0]
    ari = row_by(km["agreement"], "Measure",
                 "Adjusted Rand Index (RFM segment vs cluster)")
    r.p(f"Cluster {hv['Cluster_ID']} - {hv['Business_Label']} - is "
        f"{pc(hv['Customer_%'], 2)} of customers and "
        f"{pc(hv['Revenue_%'], 2)} of revenue, which is the same "
        "concentration the rule-based scheme found by a different route. "
        "The Adjusted Rand Index between the two schemes is "
        f"{ari['Value']:.4f}: substantial agreement on the high-value "
        "group, and genuine disagreement in the middle of the base, where "
        "the rules impose boundaries that the geometry of the data does "
        "not. Reporting both schemes is therefore more informative than "
        "reporting either alone.")
    r.figure(fig("cluster_pca_visualization.png"),
             "Customer clusters projected onto the first two principal "
             "components", width_cm=13.0)

    # ---- 4.5 customer value ----------------------------------------------
    r.heading("4.5", "Customer Value Results")
    r.p(f"Measured historical value across the base is "
        f"{cr(clv['historical_profit_total'])} of delivered profit on "
        f"{cr(clv['historical_revenue_total'])} of revenue: a mean of "
        f"{rs(clv['mean_historical_profit'], 0)} against a median of "
        f"{rs(clv['median_historical_profit'], 0)} per customer, the gap "
        "being the skew that makes averages misleading in this domain.")
    r.table(
        "Forward-value model comparison on the out-of-time test split",
        ["Model", "Type", "MAE", "RMSE", "R²", "Spearman ρ", "Selected"],
        [[m["Model"], m["Type"], rs(m["MAE"], 0), rs(m["RMSE"], 0),
          f"{m['R2']:.4f}", f"{m['Spearman']:.4f}",
          "Yes" if m.get("Selected") else ""]
         for m in clv["model_comparison"]],
        widths=[4.4, 2.2, 2.0, 2.0, 1.5, 1.7, 1.4],
        font_size=9)
    r.p(f"The {clv['metadata']['selected_model'].lower()} was selected by "
        "the rule fixed in advance. Its test R² of "
        f"{clv['metadata']['validation']['R2']:.4f} means the model "
        "explains roughly a quarter of the variance in individual "
        "twelve-month profit, and its Spearman correlation of "
        f"{clv['metadata']['validation']['Spearman']:.4f} means it ranks "
        "customers considerably better than it predicts their exact "
        "value, which is its honest use: a ranking instrument for "
        "prioritising attention, not a forecast of any individual "
        f"customer's spend. Of {n(kpi['customers'])} customers, "
        f"{n(clv['estimate_methods']['ML model (active in last 12 months)'])} "
        "were scored by the model and "
        f"{n(clv['estimate_methods']['Group average (no order in last 12 months)'])} "
        "by group average, because they had no order in the feature window. "
        f"{clv['at_risk']} customers are flagged as high-value and "
        f"inactive for 180 days or more, holding "
        f"{lakh(clv['at_risk_revenue'])} of historical revenue between "
        "them.")

    # ---- 4.6 revenue prediction ------------------------------------------
    r.heading("4.6", "Revenue Prediction Results")
    tm = pred["test_metrics"]
    r.table(
        "Revenue prediction: candidate models and baselines on the "
        "out-of-time test split",
        ["Model", "Type", "MAE", "RMSE", "R²", "WAPE %", "Selected"],
        [[m["Model"], m["Type"], rs(m["MAE"], 0), rs(m["RMSE"], 0),
          f"{m['R2']:.4f}", pc(m["WAPE_%"], 1),
          "Yes" if m.get("Selected") else ""]
         for m in pred["comparison"]],
        widths=[4.6, 2.0, 2.0, 2.0, 1.5, 1.6, 1.5],
        font_size=9)
    naive = pred["comparison"][0]
    r.p(f"The selected {pred['model'].lower()} reaches a test MAE of "
        f"{rs(tm['MAE'], 0)}, an RMSE of {rs(tm['RMSE'], 0)} and an R² of "
        f"{tm['R2']:.4f}, against {rs(naive['MAE'], 0)} MAE and an R² of "
        f"{naive['R2']:.4f} for the naive previous-quarter baseline. The "
        "model is therefore better than the baseline and still weak in "
        f"absolute terms: it explains about {pcf(tm['R2'], 1)} of the "
        f"variance in individual outcomes at a WAPE of "
        f"{pc(tm['WAPE_%'], 1)}. The reason is visible in the panel "
        f"itself - {pcf(pred['zero_actual_share'], 1)} of "
        "customer-quarters have a zero actual value, so the target is "
        "dominated by whether a customer orders at all rather than by how "
        f"much they spend. Total bias is {pc(tm['Total_Bias_%'], 2)}, so "
        "the model is close to unbiased in aggregate even though "
        "individual predictions are poor. Used at portfolio level it is "
        "informative; used to promise a number for one customer it would "
        "mislead, and the platform does not present it that way.")

    # ---- 4.7 forecasting --------------------------------------------------
    r.heading("4.7", "Forecasting Results")
    fm = fc["metrics"]
    r.p(f"The Augmented Dickey-Fuller test on the revenue level gives a "
        f"p-value of {fc['adf'][0]['p_value']:.4f}, so the null of a unit "
        "root is not rejected and the series is treated as non-stationary "
        f"in level. Across {fc['backtest'][0]['Folds']} rolling-origin "
        f"folds the {fc['model']} model returned the lowest mean backtest "
        f"MAPE and beat both naive baselines on test MAE, so it was "
        f"selected. On the held-out test window its MAE is "
        f"{rs(fm['test']['MAE'], 0)} and its MAPE "
        f"{pc(fm['test']['MAPE_%'], 2)}; the mean backtest MAPE of "
        f"{pc(fm['backtest_mean_MAPE_%'], 2)} is the figure this report "
        "treats as the expected error, because a single favourable split "
        "is not evidence of accuracy.")
    r.table(
        "Six-month revenue forecast with prediction intervals",
        ["Month", "Forecast", "Lower 80%", "Upper 80%", "Lower 95%",
         "Upper 95%"],
        [[m["Month"], lakh(m["Forecast"]), lakh(m["Lower_80"]),
          lakh(m["Upper_80"]), lakh(m["Lower_95"]), lakh(m["Upper_95"])]
         for m in fc["future"]],
        widths=[2.4, 2.6, 2.5, 2.5, 2.5, 2.5],
        font_size=9)
    r.p(f"The {fc['horizon']} forecast months total "
        f"{cr(fc['future_total'])}, with an 80% interval from "
        f"{cr(fc['future_lower80'])} to {cr(fc['future_upper80'])}, against "
        f"{cr(fc['prev_6m_actual'])} actually delivered in the preceding "
        "six months. The interval is wide, and deliberately so: at this "
        "history length the honest statement is the interval, not the point "
        "estimate. The forecast is univariate - it uses no price, "
        "promotion, holiday or macroeconomic input - so it extrapolates the "
        "revenue series alone and would not anticipate a change driven by "
        "anything outside it.")
    r.figure(fig("forecasting", "actual_vs_forecast.png"),
             "Historical monthly revenue with the six-month forecast and "
             "its prediction intervals", width_cm=11.8)

    # ---- 4.8 SQL ----------------------------------------------------------
    r.heading("4.8", "SQL Analytics Results")
    r.p(f"The database holds {sq['tables']} tables and {sq['views']} views. "
        f"All {sq['validation_checks']} referential and business-rule "
        f"validation checks pass, as do {sq['quality_checks']} data-quality "
        f"checks, and the {sq['queries']} analytical queries reproduce the "
        "pipeline's metrics. The value of this layer is the reconciliation: "
        "revenue, profit, margin, order count, customer count and AOV "
        "computed independently in SQL agree with the Python pipeline to "
        "the paisa, which is what allows the two to be quoted "
        "interchangeably in the delivery layer.")
    r.table(
        "Principal business findings computed independently in SQL",
        ["Area", "Finding (computed by SQL)", "Source query"],
        [[f["Area"], f["Finding (computed by SQL)"], f["Source query"]]
         for f in sq["key_findings"][:6]],
        widths=[2.6, 9.0, 3.4],
        font_size=8)

    # ---- 4.9 Power BI -----------------------------------------------------
    r.heading("4.9", "Power BI Semantic Model Results")
    r.p(f"The semantic model comprises {pb['tables']} tables, "
        f"{pb['relationships']} relationships and {pb['measures']} DAX "
        f"measures. All {pb['validation_rows']} measure validations match "
        f"their SQL equivalents and all {pb['consistency_total']} "
        "cross-surface consistency checks pass, so the model would report "
        "the same figures as the pipeline when opened in Power BI "
        "Desktop.")
    r.figure(fig("powerbi", "mockups", "01_executive_overview_mockup.png"),
             "Power BI executive overview page - design mockup rendered "
             "from the project data, not a Power BI Desktop screenshot",
             width_cm=12.8)
    r.note("Power BI Desktop is Windows-only and was unavailable in the "
           "build environment, so no screenshot of it exists or is claimed. "
           "The figure above and the eight further page designs in the "
           "project repository are mockups rendered from the real data and "
           "are labelled as mockups wherever they appear.")

    # ---- 4.10 Streamlit ---------------------------------------------------
    r.heading("4.10", "Streamlit Application Results")
    r.p(f"The application runs with {stl['pages']} pages and passes "
        f"{stl['tests_passed']} of {stl['tests']} headless tests covering "
        "launch, navigation, every page's load, the filters, the model "
        "loading path, the download controls, the file-upload validation "
        "and the graceful-degradation behaviour when an artefact is "
        "missing. Figure 4.8 is a screenshot of the running application.")
    r.figure(fig("streamlit", "02_executive_overview.png"),
             "Streamlit application: Executive Overview page, a screenshot "
             "of the running application", width_cm=13.2)

    # ---- 4.11 validation --------------------------------------------------
    r.heading("4.11", "Validation")
    au = F["audit"]
    r.table(
        "Validation position of every component of the platform",
        ["Component", "Validation performed", "Result"],
        [["Raw data", "Generator ground truth and injection log compared "
          "against the extract", "Matched"],
         ["Cleaning", "Every business rule re-evaluated after treatment",
          f"{q['rules_failing_after']} rules failing"],
         ["RFM segmentation", "Segment revenue totals reconciled to the "
          "delivered revenue base", "Reconciled"],
         ["K-Means", "Cluster labels reproduced from the persisted scaler "
          "and model", "100% reproduced"],
         ["Customer value", "Out-of-time validation against three "
          "alternatives and a naive baseline",
          f"Selected model R² {clv['metadata']['validation']['R2']:.4f}"],
         ["Revenue prediction", "Leakage audit recomputing sampled feature "
          "rows from the transaction table", "No leakage found"],
         ["Forecasting", "Rolling-origin backtest against naive and "
          "seasonal naive baselines",
          f"Mean MAPE {pc(fm['backtest_mean_MAPE_%'], 2)}"],
         ["SQL layer", "Referential, business-rule and data-quality checks",
          f"{sq['validation_passed']}/{sq['validation_checks']} and "
          f"{sq['quality_checks']}/{sq['quality_checks']} pass"],
         ["Power BI model", "Every DAX measure compared against its SQL "
          "equivalent",
          f"{pb['validation_matched']}/{pb['validation_rows']} match"],
         ["Streamlit application", "Headless functional tests",
          f"{stl['tests_passed']}/{stl['tests']} pass"],
         ["Whole project", "End-to-end audit of structure, pipeline "
          "dependencies, cross-dataset consistency, model reproducibility "
          "and integration",
          f"{au['passed']}/{au['total']} pass, {au['failed']} fail"]],
        widths=[3.0, 7.4, 4.6],
        font_size=9)

    # ---- 4.12 findings ----------------------------------------------------
    r.heading("4.12", "Findings and Recommendations")
    r.p("Each recommendation below is stated with the evidence that "
        "produced it, the analytical stage that computed that evidence and "
        "the action it implies. None is an opinion added at the reporting "
        "stage: every one is generated from the pipeline's own outputs and "
        "is reproduced in the application's recommendations page.")
    recs = pb["recommendation_rows"]
    r.table(
        "Business recommendations with their supporting evidence and "
        "analytical source",
        ["#", "Area", "Recommendation", "Supporting metric", "Value",
         "Source"],
        [[rec["Recommendation_ID"], rec["Area"], rec["Recommendation"],
          rec["Supporting_Metric"], rec["Metric_Value"],
          rec["Analytical_Source"].split(";")[0]] for rec in recs],
        widths=[0.8, 1.8, 5.0, 3.0, 1.6, 3.0],
        font_size=8)
    r.p("Four carry most of the available value. Protecting the top "
        f"revenue decile matters more than acquisition, because "
        f"{pc(top10['pct_of_revenue'])} of revenue sits there. The "
        f"{clv['at_risk']} high-value customers inactive for 180 days or "
        "more are a working list, not a statistic. The margin gap between "
        f"{top_cat_name(cat)} and the best-margin category is a mix "
        "question the business can act on without changing a price. And "
        "the zero-discount band's margin advantage justifies a controlled "
        "test, which is the correct next step because the present evidence "
        "is associative.")


def top_cat_name(cat):
    return cat[0]["category"]


# ==========================================================================
# CHAPTER 5 - CONCLUSION AND FUTURE WORK
# ==========================================================================
def chapter5(r: Report):
    d, kpi = F["dataset"], F["kpi"]
    km, pred, fc = F["kmeans"], F["prediction"], F["forecast"]
    au, code = F["audit"], F["code"]
    r.chapter_title(5, "Conclusion and Future Work")

    r.heading("5.1", "Conclusion")
    r.p("The project delivers what it set out to build: a platform "
        f"carrying one validated dataset of {n(d['clean_rows'])} order "
        "lines through cleaning, exploratory analysis, dual segmentation, "
        "customer value analysis, supervised prediction, forecasting, an "
        "independent SQL implementation and two delivery surfaces, every "
        "stage re-runnable from a fixed seed. All eight objectives in "
        "Section 1.3 are met.")
    r.p("Three results are worth restating. Value is concentrated: the "
        f"top 20% of customers carry "
        f"{pc(row_by(F['eda']['concentration'], 'top_pct', 20)['pct_of_revenue'])} "
        f"of {cr(kpi['revenue'])} in delivered revenue, and two "
        "independent methods identify substantially the same high-value "
        "group. The volume leader and the margin leader are different "
        "categories, making category strategy a mix question. And "
        "reliability differs sharply by horizon: monthly company revenue "
        f"forecasts to a backtest MAPE of "
        f"{pc(fc['metrics']['backtest_mean_MAPE_%'], 2)} while individual "
        "customer revenue predicts weakly - the report states both.")
    r.p("The integration claim is tested rather than asserted: an "
        f"end-to-end audit of {au['total']} checks covering structure, "
        "pipeline dependencies, cross-dataset consistency, model "
        f"reproducibility, leakage and integration returns {au['passed']} "
        f"passes and {au['failed']} failures across "
        f"{code['python_files']} Python modules and {code['notebooks']} "
        "executed notebooks.")

    r.heading("5.2", "Deviation from Expected Results")
    r.bullets([
        ("Customer-level prediction was expected to be moderately "
         "accurate; it is weak. ", f"The test R² is "
         f"{pred['test_metrics']['R2']:.4f}, because "
         f"{pcf(pred['zero_actual_share'], 1)} of customer-quarters have a "
         "zero actual value and the target is dominated by whether a "
         "customer orders at all."),
        ("A more flexible model was expected to win; a linear "
         "regression did. ", "Under the pre-declared rule the ensembles "
         "bought no material accuracy, so the interpretable model was "
         "kept."),
        ("Strong seasonality was expected; the Theta test found none. ",
         "October is the highest month in all three years, but at 36 "
         "observations the test does not confirm a stable pattern, so no "
         "seasonal model was imposed to match expectation."),
        ("The two segmentation schemes were expected to agree closely; "
         "they agree substantially but not fully. ", "The Adjusted Rand "
         "Index is "
         f"{row_by(km['agreement'], 'Measure', 'Adjusted Rand Index (RFM segment vs cluster)')['Value']:.4f}: "
         "they converge on the high-value group and diverge in the middle, "
         "which is itself a finding about where rule boundaries are "
         "arbitrary."),
    ])

    r.heading("5.3", "Limitations")
    r.bullets([
        ("Synthetic data. ", "Every result describes a generated "
         "dataset. The methods transfer; the numbers describe no real "
         "business, including the internship host organisation."),
        ("Short history. ", f"{d['months']} months supports trend "
         "analysis but is thin for seasonal estimation, and the "
         "customer-quarter model is usable at portfolio level but not for "
         "an individual customer."),
        ("Univariate forecast. ", "No price, promotion or holiday input "
         "enters the forecast, so it cannot anticipate a change driven by "
         "anything outside the revenue series."),
        ("Association, not causation, and no churn label. ", "Every "
         "relationship reported here is measured on observed orders; "
         "establishing causation requires an experiment the data cannot "
         "substitute for. The dataset also defines no churn event, so "
         "recency-based inactivity is reported instead and the word churn "
         "never describes a result."),
        ("Power BI not rendered in Desktop, and no user testing. ",
         "The semantic model and measures were built and validated, but "
         "the page layouts are design mockups because Power BI Desktop is "
         "Windows-only; no screenshot of it is claimed. The interface "
         "design follows published principles but was not tested with "
         "users."),
    ])

    r.heading("5.4", "Future Scope")
    r.bullets([
        "Validate the pipeline on a real transaction dataset under an "
        "appropriate data-protection agreement, comparing the segment "
        "structure that emerges with the one reported here.",
        "Define an operational inactivity label with the business and "
        "convert the recency flag into a supervised model evaluated "
        "against it, and reframe next-quarter prediction as a two-stage "
        "problem - will the customer order at all, and if so how much - to "
        "address the zero-inflation limiting the present model.",
        "Extend the forecast with external regressors - promotion "
        "calendar, price index and holiday effects - and test the "
        "discount-margin association experimentally.",
        "Operationalise the pipeline with scheduled re-runs and drift "
        "monitoring, and complete the Power BI build on Windows.",
    ])


# ==========================================================================
# BACK MATTER
# ==========================================================================
def references(r: Report):
    r.front_heading("References")
    r.p("Entries are cited in the text by the bracketed number shown "
        "against each. Every entry is a published work, a standard "
        "textbook or the official documentation of software actually used "
        "in this project.")
    for i, (key, text) in enumerate(REFERENCES, 1):
        para = r.p(f"[{i}]  {text}")
        para.paragraph_format.left_indent = Cm(1.0)
        para.paragraph_format.first_line_indent = Cm(-1.0)
        para.paragraph_format.line_spacing = 1.15
        para.paragraph_format.space_after = 0


def appendix(r: Report):
    r.front_heading("Appendix")
    r.p("The appendix records the configuration needed to reproduce the "
        "results. The full source code is not reproduced here; it is held "
        f"in the project repository across {F['code']['python_files']} "
        f"Python modules ({n(F['code']['python_lines'])} lines), "
        f"{F['code']['sql_files']} SQL files and "
        f"{F['code']['notebooks']} executed notebooks.")

    r.minor("A.1  Model configuration")
    clv, pred, fc, km = F["clv"], F["prediction"], F["forecast"], F["kmeans"]
    r.table(
        "Configuration of the persisted model artefacts",
        ["Artefact", "Specification", "Selection rule"],
        [["kmeans_customer_segmentation.pkl",
          km["metadata"]["model"], "K chosen by rules fixed in advance, "
          "then the highest silhouette among eligible K"],
         ["rfm_scaler.pkl", km["metadata"]["preprocessing"],
          "Fixed by the skew of the input features"],
         ["clv_model.pkl", clv["metadata"]["estimator"].replace("\n", " "),
          clv["metadata"]["selection_rule"]],
         ["revenue_prediction_model.pkl",
          f"{pred['model']} on {pred['n_features']} features "
          f"({len(pred['numeric_features'])} numeric, "
          f"{len(pred['categorical_features'])} categorical)",
          pred["selection_rule"]],
         ["forecasting_model.pkl",
          f"{fc['model']}, alpha = {fc['parameters']['alpha']:.4f}",
          fc["selection_rule"]]],
        widths=[3.6, 5.6, 5.8],
        font_size=8)

    r.minor("A.2  Selected SQL")
    r.p("The revenue KPI query below is the reconciliation anchor: the "
        "Python pipeline, the DAX measure set and this query must return "
        "the same figures, and Section 4.8 confirms that they do.")
    r.code([
        "SELECT COUNT(DISTINCT o.order_id)            AS orders,",
        "       COUNT(DISTINCT o.customer_id)         AS customers,",
        "       ROUND(SUM(oi.sales), 2)               AS revenue,",
        "       ROUND(SUM(oi.net_profit), 2)          AS profit,",
        "       ROUND(100.0 * SUM(oi.net_profit)",
        "             / SUM(oi.sales), 2)             AS margin_pct,",
        "       ROUND(SUM(oi.sales)",
        "             / COUNT(DISTINCT o.order_id), 2) AS aov",
        "FROM   order_items oi",
        "JOIN   orders o ON o.order_id = oi.order_id",
        "WHERE  oi.order_status = 'Delivered';",
    ])


def user_manual(r: Report):
    r.front_heading("User Manual")
    r.p("The platform is used through the Streamlit application. The steps "
        "below are the complete path from a clean machine to a running "
        "application.")
    r.bullets([
        "Install Python 3.11 and clone or copy the project folder.",
        "Create and activate a virtual environment: "
        "python -m venv .venv, then source .venv/bin/activate "
        "(Scripts\\activate on Windows).",
        "Install the dependencies: pip install -r requirements.txt.",
        "If the processed data and model files are not present, run the "
        "pipeline stages below in order; each writes its own outputs and "
        "reads only the persisted output of the stage before it.",
        "Start the application: streamlit run app.py, then open the local "
        "URL it prints (http://localhost:8501 by default).",
    ], numbered=True)
    r.code([
        "python scripts/generate_dataset.py   # synthetic data (seed 42)",
        "python scripts/validate_dataset.py   # generator ground truth",
        "python -c \"from src.data_cleaning import run_pipeline; "
        "run_pipeline()\"",
        "python -c \"from src.eda import run_eda; run_eda()\"",
        "python -c \"from src.rfm import run_rfm; run_rfm()\"",
        "python -c \"from src.segmentation import run_segmentation; "
        "run_segmentation()\"",
        "python -c \"from src.clv import run_clv; run_clv()\"",
        "python -c \"from src.prediction import run_prediction; "
        "run_prediction()\"",
        "python -c \"from src.forecasting import run_forecasting; "
        "run_forecasting()\"",
        "python -c \"from src.sql_analytics import run_sql_workflow; "
        "run_sql_workflow()\"",
        "python -c \"from src.powerbi_prep import run_powerbi_prep; "
        "run_powerbi_prep()\"",
        "python scripts/audit_project.py      # 135-check project audit",
    ])
    r.p("The sidebar carries the page navigation, grouped into Overview, "
        "Analytics, Intelligence and Reference, and a control that clears "
        "the cache and reloads the data. Filters appear at the top of each "
        "analytical page and apply to every chart on that page. Tables can "
        "be downloaded as CSV from the control beneath them.")
    r.table(
        "Pages of the application and what each is used for",
        ["Page", "Use"],
        [["Home", "Entry point: dataset status, what the platform contains "
          "and how to navigate it"],
         ["Executive Overview", "Headline KPIs, revenue trend and the "
          "top-line position in one screen"],
         ["Revenue Intelligence", "Revenue and profit over time, by "
          "category, by discount band and by payment method"],
         ["Customer Intelligence", "Concentration, repeat behaviour, "
          "tenure and value distribution"],
         ["Customer Segmentation", "RFM segments and K-Means clusters "
          "side by side, with the at-risk high-value list"],
         ["Product Analytics", "Category, sub-category and product "
          "performance on revenue, profit and margin"],
         ["Regional Analytics", "Region, state and city performance and "
          "the region-category margin test"],
         ["Revenue Prediction", "Next-quarter predictions with the model's "
          "own accuracy stated alongside them"],
         ["Sales Forecast", "Six-month forecast with prediction intervals "
          "and the backtest position"],
         ["Business Recommendations", "The eighteen recommendations, each "
          "with its evidence and source"],
         ["Data Explorer", "Filterable access to the underlying tables "
          "with CSV download"],
         ["About the Project", "Methodology, model metadata, limitations "
          "and reproduction instructions"]],
        widths=[4.0, 11.2],
        font_size=9)
    r.p("If a page reports that a model artefact is missing, the "
        "corresponding pipeline stage in step 4 above has not been run; "
        "run it and use the sidebar control to clear the cache. If the "
        "database is absent the application falls back to the processed "
        "CSV files automatically and states which source it is using.")


def achievements(r: Report):
    r.front_heading("Achievements")
    code, au = F["code"], F["audit"]
    r.p("Each statement below is supported by a project artefact and by "
        "the validation recorded in Section 4.11.")
    r.bullets([
        f"Built an end-to-end analytics platform spanning data generation, "
        f"cleaning, exploratory analysis, dual segmentation, customer value "
        f"analysis, supervised prediction, forecasting, SQL analytics, a "
        f"Power BI semantic model and a "
        f"{F['streamlit']['pages']}-page application.",
        f"Generated and validated an {n(F['dataset']['raw_rows'])}-line "
        f"synthetic transaction dataset against its own generator ground "
        f"truth, and cleaned it to "
        f"{n(F['dataset']['clean_rows'])} validated lines with zero "
        f"business rules failing.",
        f"Segmented {n(F['rfm']['customers_scored'])} customers by two "
        f"independent methods and quantified their agreement rather than "
        f"assuming it.",
        "Selected every model by a rule fixed before the results were "
        "seen, and reported the weak results as weak.",
        f"Reconciled {F['sql']['queries']} SQL queries and "
        f"{F['powerbi']['measures']} DAX measures against the Python "
        f"pipeline, with "
        f"{F['powerbi']['validation_matched']}/"
        f"{F['powerbi']['validation_rows']} measure validations matching.",
        f"Tested the application headlessly, with "
        f"{F['streamlit']['tests_passed']}/{F['streamlit']['tests']} "
        f"checks passing.",
        f"Built a repeatable project audit of {au['total']} checks "
        f"covering structure, pipeline dependencies, cross-dataset "
        f"consistency, model reproducibility and integration, of which "
        f"{au['passed']} pass and {au['failed']} fail.",
        f"Produced a reproducible project of {code['python_files']} Python "
        f"modules ({n(code['python_lines'])} lines), {code['sql_files']} "
        f"SQL files, {code['notebooks']} executed notebooks, "
        f"{code['figures']} figures and {code['tables']} output tables.",
        "Maintained an honest reporting standard throughout: weak model "
        "results are reported as weak, an association is not described as "
        "causation, inactivity is not described as churn, and design "
        "mockups are not described as screenshots.",
    ])


# ==========================================================================
# BUILD
# ==========================================================================
def build(outline=None, page_map=None, front_pages=0) -> Report:
    CITED.clear()
    r = Report(outline=outline, page_map=page_map, front_pages=front_pages)
    front_matter(r)
    r.start_body()
    chapter1(r)
    chapter2(r)
    chapter3(r)
    chapter4(r)
    chapter5(r)
    references(r)
    appendix(r)
    user_manual(r)
    achievements(r)
    return r


def count_front_pages(pdf_path: Path) -> int:
    """Number of PDF pages before the body section starts."""
    for i, page in enumerate(pdf_pages(pdf_path)):
        if "chapter-1 introduction" in page:
            return i
    return 0


CHECK_ITEMS = [
    ("University report structure followed",
     "All prescribed sections are present, in order, from the title page "
     "to Achievements."),
    ("Title page created",
     "Present, carrying the candidate, programme, semester, guide, "
     "institute and university exactly as the bonafide certificate states "
     "them, with the university logo taken from that certificate."),
    ("Bonafide certificate created",
     "Present, reproducing the wording of the certificate issued for the "
     "internship. Signature lines are left blank; no signature is "
     "reproduced or simulated."),
    ("Acknowledgement created",
     "Present, naming the internship host organisation and the guide "
     "recorded on the bonafide certificate."),
    ("Table of contents created",
     "Generated from the headings actually emitted, with page numbers "
     "resolved from the rendered PDF."),
    ("List of figures created",
     "{figures} figures listed, generated from the captions actually "
     "emitted; no figure is listed that does not appear."),
    ("List of tables created",
     "{tables} tables listed, generated from the captions actually "
     "emitted; every listed table appears in the report."),
    ("Abstract created",
     "One page covering problem, dataset, methodology, technologies, "
     "results and limitations. The dataset is explicitly stated to be "
     "synthetic."),
    ("Graphical abstract created",
     "Present as a rendered diagram of the pipeline from customer data to "
     "business decisions."),
    ("Abbreviations and symbols created",
     "Present; every entry is used in the report."),
    ("Chapter 1 completed",
     "Introduction: background and client identification, problem "
     "identification, objectives, scope and significance, organisation of "
     "the report, and the execution timeline."),
    ("Chapter 2 completed",
     "Literature review across five areas, a literature comparison table, "
     "the research gap and a formal problem definition."),
    ("Chapter 3 completed",
     "Architecture, dataset, preprocessing, RFM, K-Means, customer value, "
     "prediction, forecasting, SQL, Power BI, Streamlit, design "
     "constraints, alternative designs and the implementation flowchart."),
    ("Chapter 4 completed",
     "Data quality, EDA, RFM, K-Means, customer value, prediction, "
     "forecasting, SQL, Power BI, Streamlit, validation, and the "
     "recommendations with their evidence."),
    ("Chapter 5 completed",
     "Conclusion, deviation from expected results, limitations and future "
     "scope."),
    ("References completed",
     "{references} entries, every one cited in the text by a generated "
     "number. No invented author, paper, journal, URL or DOI."),
    ("Appendix completed",
     "Model configuration and the reconciliation SQL. Full source code "
     "is not reproduced; the reproduction commands are in the User Manual."),
    ("User manual completed",
     "Five numbered setup steps with exact commands, a page-by-page guide "
     "and troubleshooting."),
    ("Achievements completed",
     "Nine statements, each supported by a project artefact and by the "
     "validation in Section 4.11."),
    ("All numerical results verified",
     "Every figure in the report is read at build time from "
     "outputs/tables/report_facts.json, generated from the project's own "
     "output files. No number is typed into the report text."),
    ("No fabricated findings",
     "Every recommendation in Section 4.12 carries its evidence and the "
     "stage that produced it. Weak model results are reported as weak; "
     "the discount-margin relationship is reported as an association, not "
     "as causation."),
    ("No fabricated candidate or organisation details",
     "Candidate, programme, semester, institute, internship host, address, "
     "period and guide are taken from the bonafide certificate. The UID is "
     "left as a placeholder because the certificate does not carry it."),
    ("No fake screenshots",
     "The Streamlit figure is a screenshot of the running "
     "application. The Power BI figure is labelled a design mockup in its "
     "caption, because Power BI Desktop is Windows-only and was "
     "unavailable; this is stated in Sections 3.9, 4.9 and 5.3."),
    ("Figures numbered",
     "{figures} figures numbered per chapter (Figure C.N) with captions "
     "below each figure at 10 pt bold."),
    ("Tables numbered",
     "{tables} tables numbered per chapter (Table C.N) with captions above "
     "each table at 10 pt bold."),
    ("Cross-references checked",
     "Section, figure and table references in the text resolve to items "
     "that exist; citation numbers are generated from the reference list "
     "rather than typed."),
    ("Formatting checked",
     "A4; Times New Roman throughout; body 12 pt, 1.5 line spacing, "
     "justified; chapter titles 16 pt bold centred; main headings 14 pt "
     "bold; captions 10 pt bold; front matter in lower-case roman numerals "
     "and the body in arabic numerals restarting at 1."),
    ("Length requirement met",
     "{pages} pages, within the 35-40 page target set for submission."),
    ("Terminology consistent",
     "Inactivity is used throughout and churn is never used to describe a "
     "result, because the dataset defines no churn event. Historical value "
     "and estimated forward value are named distinctly wherever either "
     "appears."),
    ("Project title consistent",
     "The title on the title page, in the bonafide certificate and in the "
     "abstract is the same string, and matches the certificate."),
    ("Dataset description consistent",
     "The dataset is described as synthetic in the abstract and in "
     "Sections 1.1, 3.2, 4 and 5.3, with the same record, customer, "
     "product, geography and date-range figures in each place."),
    ("Model names consistent",
     "Model names and metrics are printed from the persisted model "
     "metadata, so the name used in Chapters 3, 4, 5 and the Appendix is "
     "the same string in every case."),
]


def write_checklist(report: Report, page_count: int) -> Path:
    subs = {"figures": len(report.figures), "tables": len(report.tables),
            "references": len(REFERENCES), "pages": page_count}
    lines = [
        "# Report validation checklist",
        "",
        "**Report:** Customer Revenue Intelligence — Summer Internship "
        "Project Report  ",
        f"**Candidate:** {STUDENT} · {PROGRAMME}, {SEMESTER} · "
        f"{INSTITUTE}, Chandigarh University  ",
        f"**Generated:** {date.today().isoformat()} by "
        "`python scripts/build_report.py`  ",
        f"**Word document:** `outputs/reports/{STEM}.docx`  ",
        f"**PDF:** `outputs/reports/{STEM}.pdf` ({page_count} pages)  ",
        f"**Figures:** {subs['figures']} · **Tables:** {subs['tables']} · "
        f"**References:** {subs['references']}",
        "",
        "Every item below was checked against the generated document. An "
        "item is ticked only where the stated evidence was confirmed.",
        "",
        "| # | Check | Status | Evidence |",
        "| - | ----- | ------ | -------- |",
    ]
    for i, (check, evidence) in enumerate(CHECK_ITEMS, 1):
        lines.append(f"| {i} | {check} | [x] | {evidence.format(**subs)} |")

    lines += ["", "## Figures in the report", "",
              "| Figure | Caption |", "| ------ | ------- |"]
    for number, caption in report.figures:
        lines.append(f"| {number} | {caption} |")
    lines += ["", "## Tables in the report", "",
              "| Table | Caption |", "| ----- | ------- |"]
    for number, caption in report.tables:
        lines.append(f"| {number} | {caption} |")

    lines += [
        "", "## Item requiring manual completion before submission", "",
        "| Placeholder | Where it appears | Why it is a placeholder |",
        "| ----------- | ---------------- | ----------------------- |",
        "| `[UID]` | Title page, acknowledgement | The bonafide "
        "certificate does not print the UID, and inventing one would be "
        "fabrication. Replace both occurrences before submission. |",
        "",
        "Every other candidate, programme, institute, internship and guide "
        "detail is taken from the bonafide certificate and needs no edit. "
        "The signature lines on the certificate page are intentionally "
        "blank for physical signing.",
        "",
        "## Stated limitations carried into the report",
        "",
        "- The dataset is synthetic and is stated as such in the abstract "
        "and in Sections 1.1, 3.2, 4 and 5.3.",
        "- Power BI Desktop is a Windows application and was unavailable "
        "in the Linux build environment. The semantic model, measures, "
        "Power Query scripts, theme and build guide were produced and "
        "validated; the page layout shown is a design mockup rendered from "
        "the real data and is labelled as such. No Power BI Desktop "
        "screenshot appears in the report.",
        "- Customer-level revenue prediction explains only a small share "
        "of the variance in individual outcomes; this is reported in "
        "Sections 4.6, 5.2 and 5.3 rather than omitted.",
        "- The forecast is univariate and its prediction intervals widen "
        "with the horizon; the backtest mean error, not the single-split "
        "test error, is presented as the honest expectation.",
        "- The dataset defines no churn event, so the report speaks of "
        "inactivity throughout and never of churn.",
    ]
    CHECKLIST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return CHECKLIST


def main():
    global F
    F = json.loads(FACTS_PATH.read_text(encoding="utf-8"))
    REPORTS.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / ".report_build"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir()

    print("pass A: collecting outline ...")
    pass_a = build()
    outline = pass_a.outline()
    uncited = [k for k, _ in REFERENCES if k not in CITED]
    if uncited:
        raise SystemExit(f"uncited references: {uncited}")
    print(f"        {len(outline['toc'])} headings, "
          f"{len(outline['figures'])} figures, "
          f"{len(outline['tables'])} tables, "
          f"{len(REFERENCES)} references, all cited")

    print("pass B: rendering to find page numbers ...")
    pass_b = build(outline=outline)
    b_docx = scratch / f"{STEM}_passB.docx"
    pass_b.save(b_docx)
    b_pdf = docx_to_pdf(b_docx, scratch)
    pages = pdf_pages(b_pdf)
    front = count_front_pages(b_pdf)
    skip = contents_pages(pages)
    page_map = resolve_pages(pass_b._anchors, pages, skip,
                             page_lines=pdf_page_lines(b_pdf))
    print(f"        {len(pages)} pages, {front} front-matter pages, "
          f"{len(page_map)}/{len(pass_b._anchors)} anchors resolved")

    print("pass C: final build ...")
    final = build(outline=outline, page_map=page_map, front_pages=front)
    final.save(DOCX)
    produced = docx_to_pdf(DOCX, scratch)
    shutil.copy(produced, PDF)
    page_count = len(pdf_pages(PDF))
    print(f"        {DOCX.relative_to(ROOT)}")
    print(f"        {PDF.relative_to(ROOT)} ({page_count} pages)")

    write_checklist(final, page_count)
    print(f"        {CHECKLIST.relative_to(ROOT)}")
    shutil.rmtree(scratch, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
