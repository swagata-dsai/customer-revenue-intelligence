# Live Failure Handling

*Generated 2026-09-23 by `python scripts/build_demo.py`. Every figure quoted is read from `outputs/tables/report_facts.json`; every image referenced already exists in the project.*

The principle: **name what happened, state what you will show instead, keep
moving.** Never narrate a stack trace, never apologise twice, never claim a
cause you have not verified.

The universal sentence, memorised:

> "The analytical workflow has already been validated, and I'll demonstrate the
> corresponding saved output while I troubleshoot the live component."

---

### Streamlit does not start

**Say:** "The application isn't launching — I'll show the captured output while
I look at it." Open `outputs/screenshots/` and walk files 67–78; they are real
screenshots of the same twelve pages.
**Check, calmly:** is the virtual environment active? Are you in the project
folder? Is port 8501 already in use — `streamlit run app.py --server.port 8502`.
**Do not say:** anything about what "must have" gone wrong.

### A page shows a missing-artefact message

**Say:** "That page needs a model file that isn't present in this copy — the app
degrades gracefully rather than crashing, which is deliberate and is covered by
the test suite."
**Check:** the pipeline stage that writes that artefact has run; then use the
sidebar's cache-clear control.

### Power BI does not refresh — or you are asked to open it

**Say:** "Power BI Desktop is a Windows application and wasn't available in my
build environment, so there's no `.pbix` to open. What I can show you is the
semantic model, the 84-measure DAX library, and the validation
table where 48 of 48 measures were checked against
their SQL equivalents."
**Then open:** `powerbi/dax/`, `powerbi/validation/`, and the labelled mockups
(files 57–66). This is not a failure — it is a documented limitation, so say it
in that tone.

### A model file cannot load

**Say:** "That artefact isn't loading here. The model metadata records the
library versions it was written with — scikit-learn 1.8.0 — so a version
mismatch is the first thing I'd check. Meanwhile, here are the results it
produced."
**Then open:** the relevant `models/*_metadata.json` and the saved figures.

### The dataset path is wrong

**Say:** "The path isn't resolving from this working directory. All paths are
centralised in `config.py`, so it's one place to check."
**Check:** you are in the project root; `ls data/processed/` confirms.

### A notebook throws an error

**Say:** "The notebooks are committed with their outputs already saved, so what
you're seeing on screen is the executed run. Let me scroll to the output rather
than re-execute — re-running the full pipeline takes a few minutes."
**Then:** scroll, do not re-run. Re-running live is a trap.

### No internet

**Say:** "Nothing in the demonstration needs a connection — the application
runs locally, the database is a local SQLite file, and the models are on disk."
This is true: check it is true on your machine before the viva by disabling
Wi-Fi and launching the app once.

### The laptop becomes slow

**Say:** "It's building the page cache — Streamlit re-runs the script on each
interaction, so the first load of a page is the slowest."
**Prevent it:** click through every page **before** the examiner arrives. After
that, navigation is instant. Close every other application.

### A visualisation does not load

**Say:** "The chart isn't rendering here — the same figure is in the saved
output, let me show that." Open the matching file from
`outputs/screenshots/`.
**Check:** a browser refresh usually fixes a Plotly render failure.

### A prediction takes time

**Say:** "It's applying the persisted model to the panel — the app never refits
anything, it only loads and applies." Use the pause: state the accuracy while
it runs — "test MAE ₹5,658, R² 0.0557, which is weak and I'll
explain why."

### You lose your place entirely

**Say:** "Let me take that from the top of the pipeline." Then go to the demo
order in `outputs/viva/final_demo_order.md` and restart from the nearest clean
section. Examiners do not mind a reset; they mind flailing.

### You are asked something you did not prepare

**Say:** "That value was not directly measured in this project" — or "It was
considered as a possible extension, but it was not part of the implemented
pipeline." Both are complete answers. Then offer what you *do* have.

---

## Fifteen minutes before you start

- [ ] Virtual environment active, `streamlit run app.py` already running
- [ ] Every page clicked once, so the caches are warm
- [ ] Report PDF open in a second browser tab
- [ ] `outputs/screenshots/` open in a file browser — your fallback
- [ ] A terminal open in the project folder for the SQL query
- [ ] Notifications off, other applications closed, laptop on mains power
- [ ] `outputs/viva/last_minute_revision.md` read once
