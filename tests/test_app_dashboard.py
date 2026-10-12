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
