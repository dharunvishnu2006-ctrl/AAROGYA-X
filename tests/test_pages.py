"""Drives every page of the real app; Overview equals overview_kpis."""

import json
import re

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE
from aarogya.m14_audit import health as health_module
from aarogya.m14_audit.logging_setup import shutdown_logging
from aarogya.m15_dashboard import kpis
from aarogya.m15_dashboard.brand import (
    BRAND,
    current_version,
    today_line,
)
from aarogya.platform import paths

APP_FILE = str(paths.ROOT / "app.py")
UI_DIR = paths.ROOT / "ui"
PAGES = [
    "ui/overview.py",
    "ui/patients.py",
    "ui/beds.py",
    "ui/risk_statistics.py",
    "ui/records.py",
    "ui/system_health.py",
]
CARDS = {
    "Patients": "patients",
    "Inpatients": "inpatients",
    "High-risk": "high_risk",
    "Beds occupied": "beds_occupied",
    "Beds available": "beds_available",
}
NEW_PATIENT_CSV = (
    "patient_id,name,age,gender,bmi,bp_systolic,bp_diastolic,"
    "sugar_fasting,city\n"
    "P901,Newly Uploaded,40,M,24.0,120,80,90,Pune\n"
).encode("utf-8")
COMING_NEXT_COUNT = 10


@pytest.fixture
def app(tmp_path, monkeypatch):
    # Keep 50-row seed; isolate DB, log
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "aarogya.db")
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    st.cache_resource.clear()
    at = AppTest.from_file(APP_FILE, default_timeout=60)
    at.run()
    assert not at.exception
    yield at
    st.cache_resource.clear()
    shutdown_logging()


def store_kpis(hospital_id=None):
    conn = cs.get_connection(str(paths.DB_PATH))
    try:
        return kpis.overview_kpis(conn, hospital_id)
    finally:
        conn.close()


def cards(at):
    return {m.label: m.value for m in at.metric}


@pytest.mark.parametrize("page", PAGES)
def test_every_page_runs(app, page):
    app.switch_page(page).run()
    assert not app.exception


def test_overview_is_default_page(app):
    assert set(CARDS) <= set(cards(app))


def test_overview_header_is_plain_text(app):
    assert [t.value for t in app.title] == [BRAND.name]
    captions = [c.value for c in app.caption]
    # Expect Vision then Synthetic captions
    assert captions[:2] == [
        f"Vision: {BRAND.vision}",
        "Synthetic data - not for clinical use",
    ]
    # Show Today line green, bold
    markdowns = [m.value for m in app.markdown]
    assert f":green[**{today_line(current_version())}**]" in markdowns
    assert "AAROGYA X - Hospital platform" not in [
        h.value for h in app.header
    ]
    assert not [m for m in app.markdown if m.proto.allow_html]


def code_files():
    """Returns every app, page, package and script file."""
    roots = [paths.ROOT / d for d in ("aarogya", "ui", "scripts")]
    files = [paths.ROOT / "app.py"]
    for root in roots:
        files += sorted(root.rglob("*.py"))
    return files


def test_no_html_anywhere_in_codebase():
    tags = re.compile(r"<(div|img|span|style|script)\b", re.I)
    for path in code_files():
        src = path.read_text(encoding="utf-8")
        assert "unsafe_allow_html" not in src, path.name
        assert "st.html" not in src, path.name
        assert not tags.search(src), path.name


def test_overview_cards_equal_kpis(app):
    expected = store_kpis()
    shown = cards(app)
    for label, key in CARDS.items():
        assert shown[label] == str(expected[key]), label


def test_overview_cards_follow_hospital(app):
    hospital_id = "H002"
    app.selectbox(key="overview_hospital").set_value(hospital_id).run()
    assert not app.exception
    expected = store_kpis(hospital_id)
    shown = cards(app)
    for label, key in CARDS.items():
        assert shown[label] == str(expected[key]), label
    # Expect network-wide counts unchanged
    assert shown["Patients"] == str(store_kpis()["patients"])


def test_coming_next_is_closed_list(app):
    (expander,) = [
        e for e in app.expander if e.label.startswith("Coming next")
    ]
    assert expander.proto.expanded is False
    assert len(expander.metric) == 0
    assert len(expander.button) == 0
    text = "\n".join(m.value for m in expander.markdown)
    lines = [ln for ln in text.splitlines() if "arrives in" in ln]
    assert len(lines) == COMING_NEXT_COUNT
    assert not re.search(r"\d+\s*%|₹|\$", text)


@pytest.mark.parametrize(
    "text, kind, expected",
    [
        ("PX01", "error", PATIENT_ID_FORMAT_MESSAGE),
        ("P999", "warning", "Patient not found."),
    ],
)
def test_overview_search_rejects(app, text, kind, expected):
    app.text_input(key="overview_search").input(text).run()
    assert expected in [e.value for e in getattr(app, kind)]


def test_overview_search_finds_patient(app):
    app.text_input(key="overview_search").input("P007").run()
    conn = cs.get_connection(str(paths.DB_PATH))
    try:
        name = cs.get_patient(conn, "P007")["name"]
    finally:
        conn.close()
    found = [i.value for i in app.info]
    assert any("P007" in v and name in v for v in found)


def test_upload_raises_patients_same_session(app):
    before = int(cards(app)["Patients"])
    app.switch_page("ui/records.py").run()
    app.file_uploader[0].upload("new.csv", NEW_PATIENT_CSV, "text/csv")
    app.run()
    next(b for b in app.button if b.label == "Run Ingestion").click().run()
    assert not app.exception
    app.switch_page("ui/overview.py").run()
    assert int(cards(app)["Patients"]) == before + 1


def test_sidebar_foot_shows_version_and_health(app):
    captions = [c.value for c in app.sidebar.caption]
    assert "AAROGYA X v1.1 · System healthy" in captions


def test_unhealthy_store_shows_only_health(app, monkeypatch):
    broken = {
        "status": "unhealthy",
        "store_reachable": False,
        "patient_count": None,
        "last_upload_utc": None,
    }
    monkeypatch.setattr(health_module, "health", lambda path: broken)
    app.run()
    assert not app.exception
    assert len(app.metric) == 0
    assert "Unhealthy: data store cannot be opened or queried." in [
        e.value for e in app.error
    ]
    captions = [c.value for c in app.sidebar.caption]
    assert "AAROGYA X v1.1 · System unhealthy" in captions


def page_sources():
    files = [paths.ROOT / "app.py", *UI_DIR.glob("*.py")]
    return {f.name: f.read_text(encoding="utf-8") for f in files}


def test_no_banned_words_in_pages():
    for name, src in page_sources().items():
        # Drop the Coming next names
        src = re.sub(r"COMING_NEXT = \(.*?\n\)", "", src, flags=re.S)
        assert "unsafe_allow_html" not in src, name
        for word in ("HIPAA", "DPDP", "Secure", "Compliant", "certified"):
            assert word.lower() not in src.lower(), (name, word)
        for word in (r"\bAI\b", r"\bML\b", r"predictive"):
            assert not re.search(word, src, flags=re.I), (name, word)


def test_no_delta_or_length_of_stay():
    for name, src in page_sources().items():
        assert "delta" not in src, name
        assert "vs yesterday" not in src.lower(), name
        assert "length of stay" not in src.lower(), name


def test_over_capacity_named_on_overview(tmp_path, monkeypatch):
    hospitals_csv = tmp_path / "hospitals.csv"
    hospitals_csv.write_text(
        "hospital_id,name,city,total_beds\nH001,Tiny Test,Pune,1\n",
        encoding="utf-8",
    )
    stays_csv = tmp_path / "stays.csv"
    stays_csv.write_text(
        "patient_id,hospital_id,ward,bed,admitted_at,discharged_at\n"
        "P001,H001,General,B01,2026-09-01T08:00:00+00:00,\n"
        "P002,H001,General,B02,2026-09-01T09:00:00+00:00,\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "aarogya.db")
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    monkeypatch.setattr(paths, "HOSPITALS_CSV", hospitals_csv)
    monkeypatch.setattr(paths, "STAYS_CSV", stays_csv)
    st.cache_resource.clear()
    try:
        at = AppTest.from_file(APP_FILE, default_timeout=60)
        at.run()
        assert not at.exception
        assert cards(at)["Beds available"] == "0"
        assert cards(at)["Beds occupied"] == "2"
        warnings = [w.value for w in at.warning]
        assert "Over 100% of beds: Tiny Test" in warnings
    finally:
        st.cache_resource.clear()
        shutdown_logging()


def test_flow_chart_has_fixed_height(app):
    (chart,) = app.get("vega_lite_chart")
    # Guard against a tall Row 2
    assert json.loads(chart.proto.spec)["height"] == 220
