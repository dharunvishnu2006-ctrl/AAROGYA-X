"""First-start bootstrap: create the store and seed it when empty."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Union

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe, read_patient_csv
from aarogya.m14_audit.logging_setup import log_event
from aarogya.m2_his import hospitals, loader, stays

MODULE = "m1_emr"
HIS_MODULE = "m2_his"

PathLike = Union[str, Path]


def _seed_patients(
    conn: sqlite3.Connection, seed_csv: PathLike
) -> Dict[str, Any]:
    if cs.get_all_patients(conn):
        return {"quarantined": []}
    try:
        seed_df = read_patient_csv(seed_csv)
    except FileNotFoundError:
        return {"quarantined": []}
    result = ingest_dataframe(conn, seed_df, quarantine_duplicates=True)
    log_event(
        "seed_loaded",
        MODULE,
        rows_read=result.rows_read,
        accepted=result.accepted,
        rejected=result.rejected,
    )
    return {"quarantined": result.quarantine}


def _seed_his(
    conn: sqlite3.Connection,
    hospitals_csv: Optional[PathLike],
    stays_csv: Optional[PathLike],
) -> None:
    """Loads hospitals, then stays, each only into an empty table."""
    steps = [
        (
            hospitals_csv,
            hospitals.count_hospitals,
            loader.load_hospitals,
            "hospitals_loaded",
        ),
        (stays_csv, stays.count_stays, loader.load_stays, "stays_loaded"),
    ]
    for csv_path, count, load, event in steps:
        if csv_path is None or count(conn):
            continue
        try:
            df = loader.extract_csv(csv_path)
        except FileNotFoundError:
            continue
        result = load(conn, df)
        log_event(
            event,
            HIS_MODULE,
            rows_read=result.rows_read,
            accepted=result.accepted,
            rejected=result.rejected,
        )


def bootstrap_store(
    db_path: PathLike,
    seed_csv: PathLike,
    hospitals_csv: Optional[PathLike] = None,
    stays_csv: Optional[PathLike] = None,
) -> Dict[str, Any]:
    """Creates tables; seeds only an empty store; never logs an upload."""
    conn = cs.get_connection(str(db_path))
    try:
        cs.init_db(conn)
        status = _seed_patients(conn, seed_csv)
        _seed_his(conn, hospitals_csv, stays_csv)
        return status
    finally:
        conn.close()
