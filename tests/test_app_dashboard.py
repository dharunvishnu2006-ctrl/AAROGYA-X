"""Drives the real app: every dashboard number comes from cohort_stats."""

import re

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from aarogya.m14_audit.logging_setup import shutdown_logging
from aarogya.m6_risk.cohort_stats import cohort_size, describe_vitals
from aarogya.platform import paths

APP_FILE = paths.ROOT / "app.py"


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Keep 50-row seed; isolate DB, log
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "aarogya.db")
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    st.cache_resource.clear()
    at = AppTest.from_file(str(APP_FILE), default_timeout=60)
    at.run()
    yield at
    st.cache_resource.clear()
    shutdown_logging()


def test_dashboard_renders_without_error(app):
    assert not app.exception
    assert len(app.get("imgs")) == 3


def test_metric_cards_match_cohort_stats(app):
    seed = pd.read_csv(paths.SEED_CSV)
    vitals = describe_vitals(seed)
    cards = {m.label: m.value for m in app.metric}
    assert cards["Active Cohort Size"] == str(cohort_size(seed))
    assert cards["Mean Systolic BP"] == (
        f"{vitals.loc['bp_systolic', 'mean']:.1f} mmHg"
    )
    assert cards["Mean Fasting Sugar"] == (
        f"{vitals.loc['sugar_fasting', 'mean']:.1f} mg/dL"
    )
    assert cards["Mean BMI"] == f"{vitals.loc['bmi', 'mean']:.1f}"


def test_app_source_has_no_inline_stats():
    src = APP_FILE.read_text(encoding="utf-8")
    assert not re.search(r"\.(mean|median|std)\(", src)


def _hospital_table(app):
    for frame in app.dataframe:
        if "Open Stays" in frame.value.columns:
            return frame.value
    raise AssertionError("Hospital table not rendered")


def test_hospital_tab_uses_open_stays(app):
    stays = pd.read_csv(paths.STAYS_CSV, dtype=str)
    open_counts = (
        stays[stays["discharged_at"].isna()]
        .groupby("hospital_id")["patient_id"]
        .count()
    )
    table = _hospital_table(app)
    for _, row in table.iterrows():
        expected = int(open_counts.get(row["Hospital ID"], 0))
        assert row["Open Stays"] == expected
        rate = expected / row["Total Beds"] * 100
        assert row["Occupancy Rate (%)"] == f"{rate:.1f}%"


def test_hospital_status_only_over_capacity(app):
    table = _hospital_table(app)
    assert set(table["Status"]) <= {"", "⚠️ Over capacity"}
    src = APP_FILE.read_text(encoding="utf-8")
    assert "High Load" not in src and "80.0" not in src


def test_zero_bed_hospital_shows_dash(tmp_path, monkeypatch):
    hospitals_csv = tmp_path / "hospitals.csv"
    hospitals_csv.write_text(
        "hospital_id,name,city,total_beds\nH001,No Beds,Pune,0\n",
        encoding="utf-8",
    )
    stays_csv = tmp_path / "stays.csv"
    stays_csv.write_text(
        "patient_id,hospital_id,ward,bed,admitted_at,discharged_at\n"
        "P001,H001,General,B01,2026-09-01T08:00:00+00:00,\n",
        encoding="utf-8",
    )
    # Isolate DB, log and HIS seeds
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "aarogya.db")
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    monkeypatch.setattr(paths, "HOSPITALS_CSV", hospitals_csv)
    monkeypatch.setattr(paths, "STAYS_CSV", stays_csv)
    st.cache_resource.clear()
    try:
        at = AppTest.from_file(str(APP_FILE), default_timeout=60)
        at.run()
        assert not at.exception
        row = _hospital_table(at).iloc[0]
        assert row["Open Stays"] == 1
        assert row["Occupancy Rate (%)"] == "—"
        assert row["Status"] == "⚠️ Over capacity"
    finally:
        st.cache_resource.clear()
        shutdown_logging()
