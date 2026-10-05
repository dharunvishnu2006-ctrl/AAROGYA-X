"""Shared CSV-row ingestion for the startup seed and user uploads."""

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import IO, Any, Dict, List, Union

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import Patient


@dataclass
class IngestResult:
    rows_read: int = 0
    accepted: int = 0
    skipped: int = 0
    quarantine: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def rejected(self) -> int:
        return self.rows_read - self.accepted


REQUIRED_COLUMNS = (
    "patient_id",
    "name",
    "age",
    "gender",
    "bmi",
    "bp_systolic",
    "bp_diastolic",
    "sugar_fasting",
    "city",
)


def read_patient_csv(source: Union[str, Path, IO[Any]]) -> pd.DataFrame:
    """Reads a patient CSV; accepts a BOM; strips header spaces."""
    df = pd.read_csv(source, encoding="utf-8-sig")
    df.columns = df.columns.astype(str).str.strip()
    return df


def missing_columns_reason(columns: Any) -> str:
    """Names required columns absent from columns; "" if none."""
    missing = sorted(set(REQUIRED_COLUMNS) - set(columns))
    if not missing:
        return ""
    label = "Missing column" if len(missing) == 1 else "Missing columns"
    return f"{label}: {', '.join(missing)}"


def row_to_patient(row: Any) -> Patient:
    """Builds a validated Patient from one CSV row."""
    return Patient(
        patient_id=str(row["patient_id"]).strip(),
        name=str(row["name"]).strip(),
        age=int(row["age"]),
        gender=str(row["gender"]).strip(),
        bmi=float(row["bmi"]),
        bp_systolic=float(row["bp_systolic"]),
        bp_diastolic=float(row["bp_diastolic"]),
        sugar_fasting=float(row["sugar_fasting"]),
        city=str(row["city"]).strip(),
    )


DUPLICATE_REASON = "duplicate patient_id"

# Parse upload dates with this format
UPLOAD_DATE_FORMAT = "%Y-%m-%d"


def parse_upload_date(text: str) -> date:
    """Parses upload date text with UPLOAD_DATE_FORMAT; never guesses."""
    try:
        return datetime.strptime(
            str(text).strip(), UPLOAD_DATE_FORMAT
        ).date()
    except ValueError:
        raise ValueError(
            "Date must use the format YYYY-MM-DD (e.g. 2026-10-05)."
        )


def ingest_dataframe(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    quarantine_duplicates: bool = False,
) -> IngestResult:
    """Inserts valid rows; skips duplicates; quarantines invalid rows.

    A duplicate keeps the stored row unchanged. With
    quarantine_duplicates it is also listed in the quarantine.
    """
    result = IngestResult(rows_read=len(df))
    missing_reason = missing_columns_reason(df.columns)
    if missing_reason:
        # Quarantine every row; name missing columns
        for idx, row in df.iterrows():
            result.quarantine.append(
                {
                    "row": idx + 1,
                    "id": row.get("patient_id", "N/A"),
                    "reason": missing_reason,
                }
            )
        return result
    for idx, row in df.iterrows():
        try:
            patient = row_to_patient(row)
        except (ValueError, TypeError, KeyError) as err:
            result.quarantine.append(
                {
                    "row": idx + 1,
                    "id": row.get("patient_id", "N/A"),
                    "reason": str(err),
                }
            )
            continue
        try:
            cs.insert_patient(conn, patient)
            result.accepted += 1
        except sqlite3.IntegrityError:
            result.skipped += 1
            if quarantine_duplicates:
                result.quarantine.append(
                    {
                        "row": idx + 1,
                        "id": row.get("patient_id", "N/A"),
                        "reason": DUPLICATE_REASON,
                    }
                )
    return result
