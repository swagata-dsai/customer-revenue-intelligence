# Report validation checklist

**Report:** Customer Revenue Intelligence — Summer Internship Project Report  
**Candidate:** Swagata Das · MBA - Data Science and AI, 3rd Semester · Apex Institute of Management, Chandigarh University  
**Generated:** 2026-09-23 by `python scripts/build_report.py`  
**Word document:** `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.docx`  
**PDF:** `outputs/reports/Customer_Revenue_Intelligence_Summer_Internship_Report.pdf` (40 pages)  
**Figures:** 9 · **Tables:** 16 · **References:** 38

Every item below was checked against the generated document. An item is ticked only where the stated evidence was confirmed.

| # | Check | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | University report structure followed | [x] | All prescribed sections are present, in order, from the title page to Achievements. |
| 2 | Title page created | [x] | Present, carrying the candidate, programme, semester, guide, institute and university exactly as the bonafide certificate states them, with the university logo taken from that certificate. |
| 3 | Bonafide certificate created | [x] | Present, reproducing the wording of the certificate issued for the internship. Signature lines are left blank; no signature is reproduced or simulated. |
| 4 | Acknowledgement created | [x] | Present, naming the internship host organisation and the guide recorded on the bonafide certificate. |
| 5 | Table of contents created | [x] | Generated from the headings actually emitted, with page numbers resolved from the rendered PDF. |
| 6 | List of figures created | [x] | 9 figures listed, generated from the captions actually emitted; no figure is listed that does not appear. |
| 7 | List of tables created | [x] | 16 tables listed, generated from the captions actually emitted; every listed table appears in the report. |
| 8 | Abstract created | [x] | One page covering problem, dataset, methodology, technologies, results and limitations. The dataset is explicitly stated to be synthetic. |
| 9 | Graphical abstract created | [x] | Present as a rendered diagram of the pipeline from customer data to business decisions. |
| 10 | Abbreviations and symbols created | [x] | Present; every entry is used in the report. |
| 11 | Chapter 1 completed | [x] | Introduction: background and client identification, problem identification, objectives, scope and significance, organisation of the report, and the execution timeline. |
| 12 | Chapter 2 completed | [x] | Literature review across five areas, a literature comparison table, the research gap and a formal problem definition. |
| 13 | Chapter 3 completed | [x] | Architecture, dataset, preprocessing, RFM, K-Means, customer value, prediction, forecasting, SQL, Power BI, Streamlit, design constraints, alternative designs and the implementation flowchart. |
| 14 | Chapter 4 completed | [x] | Data quality, EDA, RFM, K-Means, customer value, prediction, forecasting, SQL, Power BI, Streamlit, validation, and the recommendations with their evidence. |
| 15 | Chapter 5 completed | [x] | Conclusion, deviation from expected results, limitations and future scope. |
| 16 | References completed | [x] | 38 entries, every one cited in the text by a generated number. No invented author, paper, journal, URL or DOI. |
| 17 | Appendix completed | [x] | Model configuration and the reconciliation SQL. Full source code is not reproduced; the reproduction commands are in the User Manual. |
| 18 | User manual completed | [x] | Five numbered setup steps with exact commands, a page-by-page guide and troubleshooting. |
| 19 | Achievements completed | [x] | Nine statements, each supported by a project artefact and by the validation in Section 4.11. |
| 20 | All numerical results verified | [x] | Every figure in the report is read at build time from outputs/tables/report_facts.json, generated from the project's own output files. No number is typed into the report text. |
| 21 | No fabricated findings | [x] | Every recommendation in Section 4.12 carries its evidence and the stage that produced it. Weak model results are reported as weak; the discount-margin relationship is reported as an association, not as causation. |
| 22 | No fabricated candidate or organisation details | [x] | Candidate, programme, semester, institute, internship host, address, period and guide are taken from the bonafide certificate. The UID is left as a placeholder because the certificate does not carry it. |
| 23 | No fake screenshots | [x] | The Streamlit figure is a screenshot of the running application. The Power BI figure is labelled a design mockup in its caption, because Power BI Desktop is Windows-only and was unavailable; this is stated in Sections 3.9, 4.9 and 5.3. |
| 24 | Figures numbered | [x] | 9 figures numbered per chapter (Figure C.N) with captions below each figure at 10 pt bold. |
| 25 | Tables numbered | [x] | 16 tables numbered per chapter (Table C.N) with captions above each table at 10 pt bold. |
| 26 | Cross-references checked | [x] | Section, figure and table references in the text resolve to items that exist; citation numbers are generated from the reference list rather than typed. |
| 27 | Formatting checked | [x] | A4; Times New Roman throughout; body 12 pt, 1.5 line spacing, justified; chapter titles 16 pt bold centred; main headings 14 pt bold; captions 10 pt bold; front matter in lower-case roman numerals and the body in arabic numerals restarting at 1. |
| 28 | Length requirement met | [x] | 40 pages, within the 35-40 page target set for submission. |
| 29 | Terminology consistent | [x] | Inactivity is used throughout and churn is never used to describe a result, because the dataset defines no churn event. Historical value and estimated forward value are named distinctly wherever either appears. |
| 30 | Project title consistent | [x] | The title on the title page, in the bonafide certificate and in the abstract is the same string, and matches the certificate. |
| 31 | Dataset description consistent | [x] | The dataset is described as synthetic in the abstract and in Sections 1.1, 3.2, 4 and 5.3, with the same record, customer, product, geography and date-range figures in each place. |
| 32 | Model names consistent | [x] | Model names and metrics are printed from the persisted model metadata, so the name used in Chapters 3, 4, 5 and the Appendix is the same string in every case. |

## Figures in the report

| Figure | Caption |
| ------ | ------- |
| Figure 1.1 | Stage-wise execution timeline of the project and the deliverable produced at each stage |
| Figure 3.1 | Solution architecture, from the data source through the analytical and model layers to the three delivery surfaces |
| Figure 3.2 | Implementation flowchart of the project lifecycle, from data generation to business decision support, including the three validation gates |
| Figure 4.1 | Monthly delivered revenue across the 36-month observation window |
| Figure 4.2 | Revenue contribution by RFM segment |
| Figure 4.3 | Customer clusters projected onto the first two principal components |
| Figure 4.4 | Historical monthly revenue with the six-month forecast and its prediction intervals |
| Figure 4.5 | Power BI executive overview page - design mockup rendered from the project data, not a Power BI Desktop screenshot |
| Figure 4.6 | Streamlit application: Executive Overview page, a screenshot of the running application |

## Tables in the report

| Table | Caption |
| ----- | ------- |
| Table 2.1 | Comparison of the principal literature informing each stage of the project |
| Table 3.1 | Composition of the dataset used throughout the project |
| Table 3.2 | Business-rule validation before and after cleaning |
| Table 3.3 | Alternative designs considered at each decision point and the option selected |
| Table 4.1 | Headline performance of the delivered revenue base |
| Table 4.2 | Revenue, profit and margin by product category |
| Table 4.3 | Customer count, revenue and behaviour by RFM segment |
| Table 4.4 | Profile of the four customer clusters |
| Table 4.5 | Forward-value model comparison on the out-of-time test split |
| Table 4.6 | Revenue prediction: candidate models and baselines on the out-of-time test split |
| Table 4.7 | Six-month revenue forecast with prediction intervals |
| Table 4.8 | Principal business findings computed independently in SQL |
| Table 4.9 | Validation position of every component of the platform |
| Table 4.10 | Business recommendations with their supporting evidence and analytical source |
| Table 5.1 | Configuration of the persisted model artefacts |
| Table 5.2 | Pages of the application and what each is used for |

## Item requiring manual completion before submission

| Placeholder | Where it appears | Why it is a placeholder |
| ----------- | ---------------- | ----------------------- |
| `[UID]` | Title page, acknowledgement | The bonafide certificate does not print the UID, and inventing one would be fabrication. Replace both occurrences before submission. |

Every other candidate, programme, institute, internship and guide detail is taken from the bonafide certificate and needs no edit. The signature lines on the certificate page are intentionally blank for physical signing.

## Stated limitations carried into the report

- The dataset is synthetic and is stated as such in the abstract and in Sections 1.1, 3.2, 4 and 5.3.
- Power BI Desktop is a Windows application and was unavailable in the Linux build environment. The semantic model, measures, Power Query scripts, theme and build guide were produced and validated; the page layout shown is a design mockup rendered from the real data and is labelled as such. No Power BI Desktop screenshot appears in the report.
- Customer-level revenue prediction explains only a small share of the variance in individual outcomes; this is reported in Sections 4.6, 5.2 and 5.3 rather than omitted.
- The forecast is univariate and its prediction intervals widen with the horizon; the backtest mean error, not the single-split test error, is presented as the honest expectation.
- The dataset defines no churn event, so the report speaks of inactivity throughout and never of churn.
