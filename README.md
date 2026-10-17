# AAROGYA X

Hospital software built one version at a time: patient records, risk
bands, charts of vitals and bed occupancy per hospital. Synthetic data only.

![version](https://img.shields.io/badge/version-v1.1-blue) ![tests](https://img.shields.io/badge/tests-281%20passed-green) ![python](https://img.shields.io/badge/python-3.14-blue)

Live demo: https://aarogya-v1-nqmatcmqp2xqc2xbqtuu57.streamlit.app/

## What it does

- Stores patients in SQLite; corrections keep the old value and a reason.
- Checks every uploaded row; bad rows are quarantined with a clear reason.
- Shows each patient's risk band, and mean, median and p90 side by side.
- Shows bed occupancy per hospital from real stays (open stays / beds).
- Read-only API on this computer only, without patient names.

## What's new in v1.1

Module folders, a quality gate (`scripts/check.py`), JSON logs with no
patient data, an honest health check, identity by patient_id, one
statistics module, fixed charts, hospital stays and a Flask API.

## Run it

```
pip install -r requirements.txt
streamlit run app.py
python scripts/check.py      # needs requirements-dev.txt
```

## Numbers

| What | Value |
|---|---|
| Tests | 281 passed (`pytest -q`) |
| Mean + std, 50 rows | loop 0.040 ms, pandas 0.509 ms |
| Mean + std, 50,000 rows | loop 37.827 ms, pandas 1.429 ms |
| Chennai occupancy | 1.0% (old city formula) -> 1.6% (8 open stays / 500 beds) |

## Known limits

Not for clinical use. Risk bands come from fixed thresholds, not a
validated model. No login yet; the API runs on 127.0.0.1 only.

## Built with

Claude Code and Claude. v1.1's A1-A3 (thresholds, validation, clinical
store) were written by hand. Python, Streamlit, pandas, SQLite, Flask.

Docs: [design](docs/design.md) · [ADRs](docs/adr/) ·
[platform decisions](docs/platform_decisions.md) · [build log](docs/build_log.md)

## Versions

| Version | What | Tests |
|---|---|---|
| v1.0 | Sprint: dashboard, records, risk bands | 5 |
| v1.1 | Completion: the core record | 281 |
| v2 | Next: DSA and SQL | |