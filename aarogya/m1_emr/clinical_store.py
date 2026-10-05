import sqlite3
from typing import Any, Dict, List, Optional
from aarogya.m1_emr.models import Patient
from aarogya.platform import paths
from aarogya.platform.timeutil import utc_now_iso

ALLOWED_FIELDS = {
    "age",
    "bmi",
    "bp_systolic",
    "bp_diastolic",
    "sugar_fasting",
    "city",
}


def get_connection(db_path: str = str(paths.DB_PATH)) -> sqlite3.Connection:
    """
    Opens and configures a SQLite database connection with row access
    by column name and enforced foreign key constraints.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Initializes the schema for active patient records, the immutable
    audit ledger and the append-only upload log.
    """
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                bmi REAL NOT NULL,
                bp_systolic REAL NOT NULL,
                bp_diastolic REAL NOT NULL,
                sugar_fasting REAL NOT NULL,
                city TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patient_corrections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                field_name TEXT NOT NULL,
                old_value TEXT NOT NULL,
                new_value TEXT NOT NULL,
                reason TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT NOT NULL,
                rows_read INTEGER NOT NULL,
                accepted INTEGER NOT NULL,
                rejected INTEGER NOT NULL
            );
        """)


def insert_patient(conn: sqlite3.Connection, patient: Patient) -> None:
    """
    Inserts a validated Patient domain entity into persistent storage.
    Enforces that invalid entities cannot reach the database.
    """
    if not isinstance(patient, Patient):
        raise TypeError(
            "Expected validated Patient instance, got "
            f"{type(patient).__name__}"
        )

    now = utc_now_iso()
    with conn:
        conn.execute(
            """
            INSERT INTO patients (
                patient_id, name, age, gender, bmi,
                bp_systolic, bp_diastolic, sugar_fasting, city, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient.patient_id,
                patient.name,
                patient.age,
                patient.gender,
                patient.bmi,
                patient.bp_systolic,
                patient.bp_diastolic,
                patient.sugar_fasting,
                patient.city,
                now,
            ),
        )


def correct_patient_vital(
    conn: sqlite3.Connection,
    patient_id: str,
    field_name: str,
    new_value: Any,
    reason: str,
) -> None:
    """
    Atomically updates the current patient snapshot and appends an
    entry to the immutable audit log.

    Enforces:
      1. Field is editable.
      2. Clinical justification is non-empty.
      3. No-op corrections (new_value == old_value) are rejected.
      4. Proposed change passes Patient domain model invariants.
    """
    if field_name not in ALLOWED_FIELDS:
        raise ValueError(
            f"Field '{field_name}' is not an editable vital field."
        )

    if not reason or not reason.strip():
        raise ValueError(
            "A non-empty clinical justification is required "
            "for all corrections."
        )

    now = utc_now_iso()

    with conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patients WHERE patient_id = ?", (patient_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise KeyError(f"Patient with ID '{patient_id}' not found.")

        old_data = dict(row)
        old_val_raw = old_data[field_name]

        if str(old_val_raw) == str(new_value):
            raise ValueError(
                f"No-op correction rejected: Field '{field_name}' "
                f"is already '{new_value}'."
            )

        old_data.pop("updated_at", None)
        old_data[field_name] = new_value
        validated_patient = Patient(**old_data)
        persisted_new_val = getattr(validated_patient, field_name)

        # Interpolate column name checked against ALLOWED_FIELDS
        sql = (
            f"UPDATE patients SET {field_name} = ?, "  # nosec B608
            "updated_at = ? WHERE patient_id = ?"
        )
        cursor.execute(sql, (persisted_new_val, now, patient_id))

        cursor.execute(
            """
            INSERT INTO patient_corrections (
                patient_id, field_name, old_value, new_value, reason,
                recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id,
                field_name,
                str(old_val_raw),
                str(persisted_new_val),
                reason.strip(),
                now,
            ),
        )


def get_patient(
    conn: sqlite3.Connection, patient_id: str
) -> Optional[Dict[str, Any]]:
    """Returns the current patient record as a dict, or None."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM patients WHERE patient_id = ?", (patient_id,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def get_all_patients(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns all active patient records sorted by patient_id."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM patients ORDER BY patient_id ASC")
    return [dict(row) for row in cursor.fetchall()]


def get_patient_history(
    conn: sqlite3.Connection, patient_id: str
) -> List[Dict[str, Any]]:
    """Returns the immutable audit log for one patient, newest first."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, patient_id, field_name, old_value, new_value, reason,
               recorded_at
        FROM patient_corrections
        WHERE patient_id = ?
        ORDER BY recorded_at DESC, id DESC
        """,
        (patient_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def record_ingest(
    conn: sqlite3.Connection, rows_read: int, accepted: int, rejected: int
) -> None:
    """Appends one upload summary row; counts only, no patient data."""
    now = utc_now_iso()
    with conn:
        conn.execute(
            """
            INSERT INTO ingest_log (
                recorded_at, rows_read, accepted, rejected
            ) VALUES (?, ?, ?, ?)
            """,
            (now, rows_read, accepted, rejected),
        )


def get_ingest_log(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns all upload summaries, oldest first."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingest_log ORDER BY id ASC")
    return [dict(row) for row in cursor.fetchall()]


def get_last_ingest_utc(conn: sqlite3.Connection) -> Optional[str]:
    """Returns the newest upload time, or None before any upload."""
    row = conn.execute("SELECT MAX(recorded_at) FROM ingest_log").fetchone()
    return row[0] if row else None


def count_patients(conn: sqlite3.Connection) -> int:
    """Returns the number of active patient records."""
    return int(conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0])


def get_all_history(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Returns the immutable audit log for all patients, newest first."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, patient_id, field_name, old_value, new_value, reason,
               recorded_at
        FROM patient_corrections
        ORDER BY recorded_at DESC, id DESC
        """)
    return [dict(row) for row in cursor.fetchall()]
