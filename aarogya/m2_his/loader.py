"""M2 HIS: extract -> validate -> load for hospitals and stays CSVs.

Stays are loaded through admit and discharge, so a CSV row can never
bypass the stay rules. Rows load in file order.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, Dict, List, Sequence, Union

import pandas as pd

from aarogya.m2_his.hospitals import HOSPITAL_FIELDS, Hospital
from aarogya.m2_his.hospitals import insert_hospital
from aarogya.m2_his.stays import StayError, admit, discharge, parse_utc

STAY_FIELDS = (
    "patient_id",
    "hospital_id",
    "ward",
    "bed",
    "admitted_at",
    "discharged_at",
)
DUPLICATE_HOSPITAL_REASON = "duplicate hospital_id"


@dataclass
class LoadResult:
    rows_read: int = 0
    accepted: int = 0
    quarantine: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def rejected(self) -> int:
        return self.rows_read - self.accepted


def extract_csv(source: Union[str, Path, IO[Any]]) -> pd.DataFrame:
    """Reads a CSV as text; accepts a BOM; strips header spaces."""
    df = pd.read_csv(source, encoding="utf-8-sig", dtype=str)
    df.columns = df.columns.astype(str).str.strip()
    return df


def _missing(columns: Any, required: Sequence[str]) -> str:
    missing = sorted(set(required) - set(columns))
    if not missing:
        return ""
    label = "Missing column" if len(missing) == 1 else "Missing columns"
    return f"{label}: {', '.join(missing)}"


def _text(value: Any, label: str) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    if not text:
        raise ValueError(f"{label} cannot be empty.")
    return text


def row_to_hospital(row: Any) -> Hospital:
    """Validates one CSV row into a Hospital."""
    beds_text = _text(row["total_beds"], "total_beds")
    try:
        beds = int(beds_text)
    except ValueError:
        raise ValueError("total_beds must be a whole number.")
    if beds < 0:
        raise ValueError("total_beds cannot be negative.")
    return Hospital(
        _text(row["hospital_id"], "hospital_id"),
        _text(row["name"], "name"),
        _text(row["city"], "city"),
        beds,
    )


def _quarantine_all(df: pd.DataFrame, result: LoadResult, why: str) -> None:
    for idx in range(len(df)):
        result.quarantine.append({"row": idx + 1, "reason": why})


def load_hospitals(
    conn: sqlite3.Connection, df: pd.DataFrame
) -> LoadResult:
    """Validates and stores hospital rows; quarantines bad rows."""
    result = LoadResult(rows_read=len(df))
    missing = _missing(df.columns, HOSPITAL_FIELDS)
    if missing:
        _quarantine_all(df, result, missing)
        return result
    for idx, (_, row) in enumerate(df.iterrows()):
        try:
            insert_hospital(conn, row_to_hospital(row))
            result.accepted += 1
        except ValueError as err:
            result.quarantine.append({"row": idx + 1, "reason": str(err)})
        except sqlite3.IntegrityError:
            result.quarantine.append(
                {"row": idx + 1, "reason": DUPLICATE_HOSPITAL_REASON}
            )
    return result


def _load_stay_row(conn: sqlite3.Connection, row: Any) -> None:
    patient_id = _text(row["patient_id"], "patient_id")
    admitted_at = _text(row["admitted_at"], "admitted_at")
    left = row["discharged_at"]
    left_at = None if pd.isna(left) or not str(left).strip() else left
    # Check order before opening the stay
    if left_at is not None and parse_utc(left_at) <= parse_utc(admitted_at):
        raise StayError("Discharge must be after admission.")
    admit(
        conn,
        patient_id,
        _text(row["hospital_id"], "hospital_id"),
        _text(row["ward"], "ward"),
        _text(row["bed"], "bed"),
        admitted_at,
    )
    if left_at is not None:
        discharge(conn, patient_id, left_at)


def load_stays(conn: sqlite3.Connection, df: pd.DataFrame) -> LoadResult:
    """Loads stay rows through the stay rules; quarantines refusals."""
    result = LoadResult(rows_read=len(df))
    missing = _missing(df.columns, STAY_FIELDS)
    if missing:
        _quarantine_all(df, result, missing)
        return result
    for idx, (_, row) in enumerate(df.iterrows()):
        try:
            _load_stay_row(conn, row)
            result.accepted += 1
        except (ValueError, sqlite3.IntegrityError) as err:
            result.quarantine.append({"row": idx + 1, "reason": str(err)})
    return result
