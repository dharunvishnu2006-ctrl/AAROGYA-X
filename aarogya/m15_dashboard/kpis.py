"""Overview numbers, counted from the store. No Streamlit here.

Each function takes hospital_id=None (None = all hospitals). Patients
and high-risk counts are always network-wide: a patient record does
not belong to a hospital, only a stay does. Every read is one table;
hospital and patient names are matched in Python.
"""

import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import (
    PATIENT_ID_FORMAT_MESSAGE,
    PATIENT_ID_PATTERN,
    Patient,
)
from aarogya.m2_his.hospitals import Hospital, get_hospitals
from aarogya.m2_his.stays import get_all_stays, get_stays
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.m6_risk.cohort_stats import age_band_of
from aarogya.platform.timeutil import to_ist, to_ist_display

HIGH = "High"
ATTENTION_LIMIT = 10
STATUS_OPEN = "Inpatient"
STATUS_CLOSED = "Discharged"
STATUS_FILTERS = ("all", "open", "discharged")
NO_OPEN_STAY = "No open stay"
FLOW_COLUMNS = ["admissions", "discharges"]
RECENT_COLUMNS = [
    "Admitted (IST)",
    "Patient",
    "Hospital",
    "Ward",
    "Bed",
    "Status",
]


def _patients(conn: sqlite3.Connection) -> List[Patient]:
    rows = cs.get_all_patients(conn)
    for row in rows:
        row.pop("updated_at", None)
    return [Patient(**row) for row in rows]


def _hospitals(
    conn: sqlite3.Connection, hospital_id: Optional[str]
) -> List[Hospital]:
    found = get_hospitals(conn)
    if hospital_id is None:
        return found
    return [h for h in found if h.hospital_id == hospital_id]


def _stays(
    conn: sqlite3.Connection, hospital_id: Optional[str]
) -> List[Dict[str, Any]]:
    found = get_all_stays(conn)
    if hospital_id is None:
        return found
    return [s for s in found if s["hospital_id"] == hospital_id]


def _high_risk(conn: sqlite3.Connection) -> List[Patient]:
    # Reuse M6 scorer; triage order
    return sorted(
        p for p in _patients(conn) if score_patient_risk(p) == HIGH
    )


def _open_counts(stays: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for stay in stays:
        if stay["discharged_at"] is None:
            hid = stay["hospital_id"]
            counts[hid] = counts.get(hid, 0) + 1
    return counts


def _over_capacity(
    hospitals: List[Hospital], open_counts: Dict[str, int]
) -> List[str]:
    return [
        h.name
        for h in hospitals
        if h.is_over_capacity(open_counts.get(h.hospital_id, 0))
    ]


def overview_kpis(
    conn: sqlite3.Connection, hospital_id: Optional[str] = None
) -> Dict[str, Any]:
    """Returns the five card counts plus occupancy; never clamped."""
    hospitals = _hospitals(conn, hospital_id)
    open_counts = _open_counts(_stays(conn, hospital_id))
    beds_total = sum(h.total_beds for h in hospitals)
    occupied = sum(open_counts.get(h.hospital_id, 0) for h in hospitals)
    available = sum(
        max(h.total_beds - open_counts.get(h.hospital_id, 0), 0)
        for h in hospitals
    )
    pct = None if beds_total == 0 else round(occupied / beds_total * 100, 1)
    return {
        "patients": cs.count_patients(conn),
        "inpatients": occupied,
        "high_risk": len(_high_risk(conn)),
        "beds_total": beds_total,
        "beds_occupied": occupied,
        "beds_available": available,
        "occupancy_pct": pct,
        "over_capacity": _over_capacity(hospitals, open_counts),
    }


def recent_patients(
    conn: sqlite3.Connection,
    hospital_id: Optional[str] = None,
    n: int = 8,
    status: str = "all",
) -> List[Dict[str, Any]]:
    """Returns the newest stays first, filtered by status."""
    if status not in STATUS_FILTERS:
        raise ValueError(f"status must be one of {STATUS_FILTERS}.")
    stays = _stays(conn, hospital_id)
    if status == "open":
        stays = [s for s in stays if s["discharged_at"] is None]
    elif status == "discharged":
        stays = [s for s in stays if s["discharged_at"] is not None]
    stays.sort(
        key=lambda s: (to_ist(s["admitted_at"]), s["stay_id"]),
        reverse=True,
    )
    names = {h.hospital_id: h.name for h in get_hospitals(conn)}
    people = {p.patient_id: str(p) for p in _patients(conn)}
    return [
        {
            "Admitted (IST)": to_ist_display(s["admitted_at"]),
            "Patient": people.get(s["patient_id"], s["patient_id"]),
            "Hospital": names.get(s["hospital_id"], s["hospital_id"]),
            "Ward": s["ward"],
            "Bed": s["bed"],
            "Status": (
                STATUS_OPEN if s["discharged_at"] is None else STATUS_CLOSED
            ),
        }
        for s in stays[:n]
    ]


def patient_flow(
    conn: sqlite3.Connection, hospital_id: Optional[str] = None
) -> pd.DataFrame:
    """Counts admissions and discharges per IST day, gaps as 0."""
    events = []
    for stay in _stays(conn, hospital_id):
        events.append((to_ist(stay["admitted_at"]).date(), "admissions"))
        if stay["discharged_at"] is not None:
            day = to_ist(stay["discharged_at"]).date()
            events.append((day, "discharges"))
    if not events:
        return pd.DataFrame(columns=FLOW_COLUMNS, dtype=int)
    df = pd.DataFrame(events, columns=["day", "kind"])
    table = df.groupby(["day", "kind"]).size().unstack(fill_value=0)
    days = pd.date_range(table.index.min(), table.index.max()).date
    table = table.reindex(index=days, columns=FLOW_COLUMNS, fill_value=0)
    table.index.name = "day"
    return table.astype(int)


def needs_attention(
    conn: sqlite3.Connection, hospital_id: Optional[str] = None
) -> Dict[str, Any]:
    """Returns high-risk patients (up to 10) and full hospitals."""
    high = _high_risk(conn)
    hospitals = _hospitals(conn, hospital_id)
    open_counts = _open_counts(_stays(conn, hospital_id))
    return {
        "high_risk": [str(p) for p in high[:ATTENTION_LIMIT]],
        "high_risk_total": len(high),
        "over_capacity": _over_capacity(hospitals, open_counts),
    }


def find_patient(
    conn: sqlite3.Connection, patient_id: str
) -> Optional[Dict[str, Any]]:
    """Returns one patient's card; None if unknown; bad id raises."""
    pid = str(patient_id).strip()
    if PATIENT_ID_PATTERN.fullmatch(pid) is None:
        raise ValueError(PATIENT_ID_FORMAT_MESSAGE)
    row = cs.get_patient(conn, pid)
    if row is None:
        return None
    row.pop("updated_at", None)
    patient = Patient(**row)
    stay_text = NO_OPEN_STAY
    names = {h.hospital_id: h.name for h in get_hospitals(conn)}
    for stay in get_stays(conn, pid):
        if stay["discharged_at"] is None:
            since = to_ist_display(stay["admitted_at"])
            hospital = names.get(stay["hospital_id"], stay["hospital_id"])
            stay_text = (
                f"{hospital}, {stay['ward']}, bed {stay['bed']}, "
                f"since {since}"
            )
    return {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age_band": age_band_of(patient.age),
        "city": patient.city,
        "risk": score_patient_risk(patient),
        "stay": stay_text,
    }
