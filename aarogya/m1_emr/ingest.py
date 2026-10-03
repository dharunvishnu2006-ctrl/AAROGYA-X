"""Shared CSV-row ingestion for the startup seed and user uploads."""

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List

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
