"""Live store health check; never returns a fixed "ok"."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, Union

from aarogya.m1_emr import clinical_store as cs
from aarogya.platform import paths


def _open_existing(db_path: Union[str, Path]) -> sqlite3.Connection:
    # Open read-write only; never create
    uri = Path(db_path).resolve().as_uri() + "?mode=rw"
    return sqlite3.connect(uri, uri=True)


def health(db_path: Union[str, Path] = paths.DB_PATH) -> Dict[str, Any]:
    """Opens and queries the store now; any failure means unhealthy."""
    report: Dict[str, Any] = {
        "status": "unhealthy",
        "store_reachable": False,
        "patient_count": None,
        "last_upload_utc": None,
    }
    try:
        conn = _open_existing(db_path)
    except (sqlite3.Error, OSError):
        return report
    try:
        count = cs.count_patients(conn)
        last_upload = cs.get_last_ingest_utc(conn)
    except (sqlite3.Error, OSError):
        return report
    finally:
        conn.close()
    report.update(
        status="healthy",
        store_reachable=True,
        patient_count=count,
        last_upload_utc=last_upload,
    )
    return report
