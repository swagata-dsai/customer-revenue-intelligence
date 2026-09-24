# Student Manual Actions

*Generated 2026-09-24 by `python scripts/build_submission.py`. Every status is derived from the files on disk and from `outputs/tables/report_facts.json`. This is a packaging step: no analysis was re-run and no value was invented.*

Only tasks that remain for you. Anything already verified is not listed.

## Must do before submission

| # | Action | Where | Time |
|---|---|---|---|
| 1 | Replace `[UID]` with your university ID | Report title page **and** acknowledgement — edit `01_REPORT/Final_Internship_Report.docx`, then re-export the PDF | 3 min |
| 2 | Replace `[TO BE FILLED]` with your UID | PPT slide 1 — edit `02_PRESENTATION/Final_Internship_Presentation.pptx`, re-export the PDF | 2 min |
| 3 | Sign the bonafide certificate page | Printed report, page ii | 1 min |
| 4 | Check whether your department requires a **Declaration** | If yes, add it — wording is in `declaration_check.md` | 5 min |
| 5 | Add the internship **year** if your department wants it printed | Report title page and PPT slide 1 — the certificate does not print one | 2 min |
| 6 | Read the PPT once for spelling and tone | 22 slides | 10 min |
| 7 | Create the final ZIP | Commands in `zip_contents.md` | 2 min |
| 8 | Back up to at least three places | Local, USB, cloud, GitHub — see `backup_manifest.md` | 15 min |
| 9 | Submit per your department's instructions | — | — |

**Note on 1 and 2:** editing the `.docx` and `.pptx` directly is fine. If you
would rather regenerate them, put your UID into `UID = "[UID]"` in
`scripts/build_report.py` and `UID = "[TO BE FILLED]"` in
`scripts/build_presentation.py`, then re-run both scripts — they rebuild both
formats.

## Before the viva

| # | Action | Why | Time |
|---|---|---|---|
| 10 | Open the Streamlit app and click through **every** page once | The first load of each page builds its cache; after that navigation is instant | 5 min |
| 11 | Test the demo offline — disable Wi-Fi and launch the app | Confirms nothing needs a connection | 2 min |
| 12 | Read `09_VIVA/final_demo_order.md` | The running order and the rehearsed transitions | 10 min |
| 13 | Read `09_VIVA/last_minute_revision.md` | The numbers and the three sentences to have word-perfect | 5 min |
| 14 | Read `09_VIVA/live_failure_handling.md` | What to say if something fails live | 5 min |
| 15 | Rehearse the 3-minute explanation aloud, twice | `09_VIVA/live_demo_script.md` | 10 min |
| 16 | Carry the USB with the ZIP | If the laptop fails, the examiner can still open the report and PPT | — |

## Optional

| # | Action | Value |
|---|---|---|
| 17 | Build the Power BI `.pbix` on a Windows machine | Converts the one partial component to complete. Guide: `07_DASHBOARDS/PowerBI/POWERBI_BUILD_GUIDE.md` |
| 18 | Push to GitHub | Portfolio link and version history. Commands: `github_final_check.md` |
| 19 | Capture a terminal screenshot of the SQL query running | Optional — the SQL result charts already carry the findings |

## Not your job — already done

For reassurance, these were completed and verified: report and PPT built and
checked; all numbers reconciled across every document; 81 screenshots
assembled; the viva pack written; `README.md`, `requirements.txt`,
`.gitignore` and `LICENSE` finalised; caches cleaned; the submission package
assembled; and 135 automated checks run
(134 pass, 0 fail).
