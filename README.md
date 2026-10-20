# AAROGYA X

Hospital software built one version at a time: patient records, risk
bands, charts of the cohort's vitals and bed occupancy per hospital,
plus a standard FHIR export. Synthetic data only.

**Live demo:** https://aarogya-x.streamlit.app
**Repository:** https://github.com/dharunvishnu2006-ctrl/AAROGYA-X

![version](https://img.shields.io/badge/version-v1.1-green) ![tests](https://img.shields.io/badge/tests-362%20passed-green) ![python](https://img.shields.io/badge/python-3.14-blue)

## What it does

- Keeps patient records in SQLite; a correction keeps the old value and a reason.
- Checks every uploaded row; bad rows are quarantined with a reason a clerk can read.
- Gives each patient a risk band and shows mean, median and p90 side by side.
- Shows bed occupancy per hospital from real stays (open stays / beds).
- Exports one patient as a FHIR record (no name), through a read-only local API.

## What's new in v1.1

Module folders and a quality gate, JSON logs with no patient data, an
honest health check, identity by patient_id, one statistics module,
hospital stays and occupancy, a FHIR export (every LOINC code checked by
hand on loinc.org), one test that follows a patient through the whole
hospital, and a six-page hospital look.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
python scripts/check.py      # needs requirements-dev.txt
```

## Numbers

| What | Value |
|---|---|
| Tests | 362 passed (`pytest -q`) |
| Mean + std, 50 rows | loop 0.040 ms, pandas 0.509 ms |
| Mean + std, 50,000 rows | loop 37.827 ms, pandas 1.429 ms |
| Occupancy | 21 of 32 beds (65.6%) |

The first version divided every patient in a city by one hospital's
beds and showed Chennai at 1.0%. Occupancy now comes from open stays.

## Known limits

Not for clinical use. Risk bands come from fixed thresholds, not a
validated model. No login; the API runs on 127.0.0.1 only. FHIR export
only: no import, not tested with a real hospital system, no ABDM
connection. Age is stored, not date of birth.

## Built with

Claude Code and Claude. v1.1's A1-A3 (thresholds, validation, clinical
store) were written by hand. Python, Streamlit, pandas, SQLite, Flask,
fhir.resources.

Docs: [design](docs/design.md) · [ADRs](docs/adr/) ·
[platform decisions](docs/platform_decisions.md) · [build log](docs/build_log.md)

## Versions

| Version | What | Tests |
|---|---|---|
| v1.0 | Sprint: dashboard, records, risk bands | 5 |
| v1.1 | Completion: the core record, FHIR export, hospital look | 362 |
| v2 | Next: DSA and SQL | |