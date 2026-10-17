"""M2 HIS: hospital stays and the only copy of the stay rules.

Rules:
  1. A patient cannot have two open stays.
  2. A bed holds at most one open stay.
  3. Discharge must be after admission.
  4. A patient never admitted cannot be discharged.

Every query reads one table. Discharge fills discharged_at once and
never overwrites a set value.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List

from aarogya.m1_emr import clinical_store as cs
from aarogya.m2_his.hospitals import get_hospital


class StayError(ValueError):
    """A stay request that would break a stay rule."""


def parse_utc(text: Any) -> datetime:
    """Parses an ISO-8601 time; requires a UTC offset."""
    try:
        moment = datetime.fromisoformat(str(text).strip())
    except ValueError:
        raise StayError(
            "Stay time must be ISO-8601 with a UTC offset "
            "(e.g. 2026-09-01T08:00:00+00:00)."
        )
    if moment.tzinfo is None:
        raise StayError("Stay time has no UTC offset; refusing to guess.")
    return moment.astimezone(timezone.utc)


def _require_text(value: Any, label: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise StayError(f"{label} cannot be empty.")
    return text


def _open_stay(conn: sqlite3.Connection, patient_id: str) -> Any:
    return conn.execute(
        """
        SELECT stay_id, admitted_at FROM stays
        WHERE patient_id = ? AND discharged_at IS NULL
        """,
        (patient_id,),
    ).fetchone()


def admit(
    conn: sqlite3.Connection,
    patient_id: str,
    hospital_id: str,
    ward: str,
    bed: str,
    admitted_at: Any,
) -> int:
    """Opens one stay after checking every rule; returns stay_id."""
    ward = _require_text(ward, "Ward")
    bed = _require_text(bed, "Bed")
    stored_at = parse_utc(admitted_at).isoformat()
    if cs.get_patient(conn, patient_id) is None:
        raise StayError("Patient not found; cannot admit.")
    if get_hospital(conn, hospital_id) is None:
        raise StayError("Hospital not found; cannot admit.")
    if _open_stay(conn, patient_id) is not None:
        raise StayError("Patient already has an open stay.")
    taken = conn.execute(
        """
        SELECT 1 FROM stays
        WHERE hospital_id = ? AND ward = ? AND bed = ?
          AND discharged_at IS NULL
        """,
        (hospital_id, ward, bed),
    ).fetchone()
    if taken is not None:
        raise StayError("Bed already holds an open stay.")
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO stays (
                patient_id, hospital_id, ward, bed, admitted_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (patient_id, hospital_id, ward, bed, stored_at),
        )
    return int(cursor.lastrowid or 0)


def discharge(
    conn: sqlite3.Connection, patient_id: str, discharged_at: Any
) -> None:
    """Closes the patient's open stay; time must follow admission."""
    leaving = parse_utc(discharged_at)
    stay = _open_stay(conn, patient_id)
    if stay is None:
        ever = conn.execute(
            "SELECT 1 FROM stays WHERE patient_id = ?", (patient_id,)
        ).fetchone()
        if ever is None:
            raise StayError("Patient was never admitted; cannot discharge.")
        raise StayError("Patient has no open stay; already discharged.")
    if leaving <= parse_utc(stay[1]):
        raise StayError("Discharge must be after admission.")
    with conn:
        # Fill only a still-open stay
        conn.execute(
            """
            UPDATE stays SET discharged_at = ?
            WHERE stay_id = ? AND discharged_at IS NULL
            """,
            (leaving.isoformat(), stay[0]),
        )


def get_stays(
    conn: sqlite3.Connection, patient_id: str
) -> List[Dict[str, Any]]:
    """Returns one patient's stays, oldest first."""
    rows = conn.execute(
        "SELECT * FROM stays WHERE patient_id = ? ORDER BY stay_id ASC",
        (patient_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_open_stays(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns every open stay, oldest first."""
    rows = conn.execute(
        "SELECT * FROM stays WHERE discharged_at IS NULL "
        "ORDER BY stay_id ASC"
    ).fetchall()
    return [dict(row) for row in rows]


def count_open_stays_by_hospital(
    conn: sqlite3.Connection,
) -> Dict[str, int]:
    """Counts open stays per hospital_id; one table only."""
    rows = conn.execute("""
        SELECT hospital_id, COUNT(*) FROM stays
        WHERE discharged_at IS NULL
        GROUP BY hospital_id
        """).fetchall()
    return {row[0]: int(row[1]) for row in rows}


def count_stays(conn: sqlite3.Connection) -> int:
    """Returns the number of stored stays, open or closed."""
    return int(conn.execute("SELECT COUNT(*) FROM stays").fetchone()[0])
