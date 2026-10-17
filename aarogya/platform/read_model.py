"""Read-only views for the API: one function per route.

Each view returns plain JSON-ready data. No view returns a name.
"""

import math
import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import PATIENT_ID_PATTERN, Patient
from aarogya.m2_his.occupancy import hospital_occupancy
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.m6_risk.cohort_stats import (
    VITALS,
    age_band_of,
    cohort_size,
    describe_vitals,
)


def is_valid_patient_id(patient_id: str) -> bool:
    """True when the id matches the one patient_id format."""
    return PATIENT_ID_PATTERN.fullmatch(patient_id) is not None


def _number(value: Any) -> Optional[float]:
    number = float(value)
    return None if math.isnan(number) else number


def cohort_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Returns cohort size and per-vital stats; NaN becomes None."""
    df = pd.DataFrame(cs.get_all_patients(conn))
    if df.empty:
        return {"cohort_size": 0, "vitals": {}}
    table = describe_vitals(df)
    vitals = {
        vital: {
            stat: (int(value) if stat == "count" else _number(value))
            for stat, value in table.loc[vital].items()
        }
        for vital in table.index
    }
    return {"cohort_size": cohort_size(df), "vitals": vitals}


def patient_view(
    conn: sqlite3.Connection, patient_id: str
) -> Optional[Dict[str, Any]]:
    """Returns id, age band, city, vitals, risk; None if unknown."""
    row = cs.get_patient(conn, patient_id)
    if row is None:
        return None
    row.pop("updated_at", None)
    patient = Patient(**row)
    return {
        "patient_id": patient.patient_id,
        "age_band": age_band_of(patient.age),
        "city": patient.city,
        "vitals": {vital: getattr(patient, vital) for vital in VITALS},
        "risk": score_patient_risk(patient),
    }


def occupancy_view(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns occupancy per hospital from open stays."""
    return hospital_occupancy(conn)
