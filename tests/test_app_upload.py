"""Drives the real app: upload feedback must survive the rerun."""

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE
from aarogya.m14_audit.logging_setup import shutdown_logging
from aarogya.platform import paths

APP_FILE = str(paths.ROOT / "app.py")
BAD_ID_CSV = (
    "patient_id,name,age,gender,bmi,bp_systolic,bp_diastolic,"
    "sugar_fasting,city\n"
    "PX01,Test Person,40,M,24.0,120,80,90,Pune\n"
).encode("utf-8")


@pytest.fixture
def app(tmp_path, sample_csv, monkeypatch):
    # Point every app path into tmp_path
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "aarogya.db")
    monkeypatch.setattr(paths, "SEED_CSV", sample_csv)
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    st.cache_resource.clear()
    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.run()
    assert not at.exception
    yield at
    st.cache_resource.clear()
    shutdown_logging()


SPACED_BOM_CSV = (
    "\ufeff   patient_id, name ,age,gender,bmi,bp_systolic,bp_diastolic,"
    "sugar_fasting,city\n"
    "P101,Test Person,40,M,24.0,120,80,90,Pune\n"
).encode("utf-8")
NO_ID_CSV = (
    "name,age,gender,bmi,bp_systolic,bp_diastolic,sugar_fasting,city\n"
    "Test Person,40,M,24.0,120,80,90,Pune\n"
).encode("utf-8")


def upload(at, content):
    at.file_uploader[0].upload("up.csv", content, "text/csv").run()
    run_btn = next(b for b in at.button if b.label == "Run Ingestion")
    run_btn.click().run()
    assert not at.exception


def upload_bad_id(at):
    at.file_uploader[0].upload("bad.csv", BAD_ID_CSV, "text/csv").run()
    run_btn = next(b for b in at.button if b.label == "Run Ingestion")
    run_btn.click().run()
    assert not at.exception


def quarantine_table(at):
    tables = [d.value for d in at.sidebar.dataframe]
    return next(t for t in tables if "reason" in t.columns)


def test_bad_id_upload_shows_format_message(app):
    upload_bad_id(app)
    errors = [e.value for e in app.sidebar.error]
    assert "Quarantined 1 invalid rows." in errors
    table = quarantine_table(app)
    assert list(table["id"]) == ["PX01"]
    assert list(table["reason"]) == [PATIENT_ID_FORMAT_MESSAGE]
    conn = cs.get_connection(str(paths.DB_PATH))
    try:
        assert cs.count_patients(conn) == 4
    finally:
        conn.close()


def test_message_survives_next_rerun(app):
    upload_bad_id(app)
    app.run()
    assert not app.exception
    assert "Quarantined 1 invalid rows." in [
        e.value for e in app.sidebar.error
    ]
    table = quarantine_table(app)
    assert list(table["reason"]) == [PATIENT_ID_FORMAT_MESSAGE]


def test_spaced_bom_header_upload_accepted(app):
    upload(app, SPACED_BOM_CSV)
    assert "Ingested 1 new patients." in [
        m.value for m in app.sidebar.success
    ]
    assert not [e.value for e in app.sidebar.error]


def test_missing_column_upload_shows_reason(app):
    upload(app, NO_ID_CSV)
    table = quarantine_table(app)
    assert list(table["reason"]) == ["Missing column: patient_id"]
