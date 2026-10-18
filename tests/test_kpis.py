"""Overview numbers on a known store: exact counts, never clamped."""

import re
from datetime import date
from pathlib import Path

import pytest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE, Patient
from aarogya.m15_dashboard import kpis
from aarogya.m2_his.hospitals import Hospital, insert_hospital
from aarogya.m2_his.stays import admit, discharge

DAY1 = "2026-09-01T06:00:00+00:00"
DAY1_LATER = "2026-09-01T09:00:00+00:00"
DAY2 = "2026-09-02T06:00:00+00:00"


def high(pid, name="High Testcase"):
    return Patient(pid, name, 60, "M", 35.0, 160, 100, 200, "Chennai")


def low(pid, name="Low Testcase"):
    return Patient(pid, name, 30, "F", 22.0, 110, 70, 85, "Pune")


@pytest.fixture
def store(tmp_path):
    conn = cs.get_connection(str(tmp_path / "kpis.db"))
    cs.init_db(conn)
    for patient in [high("P001", "Asha Kumar"), low("P002"), low("P003")]:
        cs.insert_patient(conn, patient)
    insert_hospital(conn, Hospital("H001", "North Test", "Chennai", 4))
    insert_hospital(conn, Hospital("H002", "South Test", "Pune", 1))
    # Admit two, then discharge one
    admit(conn, "P001", "H001", "W1", "B1", DAY1)
    admit(conn, "P002", "H001", "W1", "B2", DAY1_LATER)
    discharge(conn, "P002", DAY2)
    admit(conn, "P003", "H002", "W1", "B1", DAY2)
    yield conn
    conn.close()


def test_overview_all_hospitals(store):
    assert kpis.overview_kpis(store) == {
        "patients": 3,
        "inpatients": 2,
        "high_risk": 1,
        "beds_total": 5,
        "beds_occupied": 2,
        "beds_available": 3,
        "occupancy_pct": 40.0,
        "over_capacity": [],
    }


def test_overview_one_hospital(store):
    result = kpis.overview_kpis(store, "H001")
    assert result["inpatients"] == 1
    assert result["beds_total"] == 4
    assert result["beds_occupied"] == 1
    assert result["beds_available"] == 3
    assert result["occupancy_pct"] == 25.0
    # Expect network-wide patient counts
    assert result["patients"] == 3
    assert result["high_risk"] == 1


def test_over_capacity_never_negative(store):
    cs.insert_patient(store, low("P004"))
    admit(store, "P004", "H002", "W1", "B2", DAY2)
    one = kpis.overview_kpis(store, "H002")
    assert one["beds_occupied"] == 2
    assert one["beds_available"] == 0
    assert one["occupancy_pct"] == 200.0
    assert one["over_capacity"] == ["South Test"]
    every = kpis.overview_kpis(store)
    # Sum per hospital, not overall
    assert every["beds_available"] == 3
    assert every["occupancy_pct"] == 60.0
    assert every["over_capacity"] == ["South Test"]


def test_zero_beds_has_no_rate(tmp_path):
    conn = cs.get_connection(str(tmp_path / "zero.db"))
    cs.init_db(conn)
    insert_hospital(conn, Hospital("H009", "No Beds", "Pune", 0))
    result = kpis.overview_kpis(conn)
    conn.close()
    assert result["occupancy_pct"] is None
    assert result["beds_available"] == 0


def test_flow_exact_rows(store):
    flow = kpis.patient_flow(store, "H001")
    assert list(flow.columns) == ["admissions", "discharges"]
    assert flow.to_dict("index") == {
        date(2026, 9, 1): {"admissions": 2, "discharges": 0},
        date(2026, 9, 2): {"admissions": 0, "discharges": 1},
    }


def test_flow_fills_gap_days(store):
    cs.insert_patient(store, low("P005"))
    admit(store, "P005", "H001", "W2", "B1", "2026-09-04T06:00:00+00:00")
    flow = kpis.patient_flow(store, "H001")
    assert list(flow.index) == [date(2026, 9, d) for d in (1, 2, 3, 4)]
    assert flow.loc[date(2026, 9, 3)].tolist() == [0, 0]


def test_flow_uses_ist_date(store):
    cs.insert_patient(store, low("P006"))
    # Expect 22:00 UTC as next IST day
    admit(store, "P006", "H001", "W2", "B1", "2026-09-02T22:00:00+00:00")
    flow = kpis.patient_flow(store, "H001")
    assert flow.loc[date(2026, 9, 3), "admissions"] == 1


def test_flow_empty_store(tmp_path):
    conn = cs.get_connection(str(tmp_path / "empty.db"))
    cs.init_db(conn)
    flow = kpis.patient_flow(conn)
    conn.close()
    assert flow.empty
    assert list(flow.columns) == ["admissions", "discharges"]


def test_recent_newest_first(store):
    rows = kpis.recent_patients(store)
    assert [r["Patient"] for r in rows] == [
        str(low("P003")),
        str(low("P002")),
        str(high("P001", "Asha Kumar")),
    ]
    assert list(rows[0]) == kpis.RECENT_COLUMNS
    assert rows[0]["Hospital"] == "South Test"
    assert rows[0]["Admitted (IST)"] == "2026-09-02 11:30 IST"


@pytest.mark.parametrize(
    "status, expected",
    [
        ("all", ["P003", "P002", "P001"]),
        ("open", ["P003", "P001"]),
        ("discharged", ["P002"]),
    ],
)
def test_recent_status_filters(store, status, expected):
    rows = kpis.recent_patients(store, status=status)
    assert [r["Patient"].split()[0] for r in rows] == expected
    wanted = {"open": {"Inpatient"}, "discharged": {"Discharged"}}
    if status in wanted:
        assert {r["Status"] for r in rows} == wanted[status]


def test_recent_limit_and_hospital(store):
    assert len(kpis.recent_patients(store, n=1)) == 1
    rows = kpis.recent_patients(store, "H002")
    assert [r["Hospital"] for r in rows] == ["South Test"]


def test_recent_rejects_unknown_status(store):
    with pytest.raises(ValueError):
        kpis.recent_patients(store, status="maybe")


def test_needs_attention(store):
    result = kpis.needs_attention(store)
    assert result["high_risk"] == [str(high("P001", "Asha Kumar"))]
    assert result["high_risk_total"] == 1
    assert result["over_capacity"] == []


def test_needs_attention_caps_at_ten(store):
    for n in range(10, 22):
        cs.insert_patient(store, high(f"P{n:03d}"))
    result = kpis.needs_attention(store)
    assert result["high_risk_total"] == 13
    assert len(result["high_risk"]) == 10
    # Expect triage order: numeric id
    assert result["high_risk"][0].startswith("P001")
    assert result["high_risk"][-1].startswith("P018")


def test_find_patient(store):
    card = kpis.find_patient(store, "P001")
    assert card["name"] == "Asha Kumar"
    assert card["risk"] == "High"
    assert card["age_band"] == "60+"
    assert card["stay"].startswith("North Test, W1, bed B1, since")
    assert kpis.find_patient(store, "P002")["stay"] == kpis.NO_OPEN_STAY
    assert kpis.find_patient(store, "P999") is None
    with pytest.raises(
        ValueError, match=re.escape(PATIENT_ID_FORMAT_MESSAGE)
    ):
        kpis.find_patient(store, "PX01")


def test_source_has_no_streamlit_or_join():
    src = Path(kpis.__file__).read_text(encoding="utf-8")
    assert "streamlit" not in src
    assert "JOIN" not in src.upper()
    assert "SELECT" not in src.upper()
