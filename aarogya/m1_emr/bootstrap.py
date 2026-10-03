"""First-start bootstrap: create the store and seed it when empty."""

from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m14_audit.logging_setup import log_event

MODULE = "m1_emr"


def bootstrap_store(
    db_path: Union[str, Path], seed_csv: Union[str, Path]
) -> Dict[str, Any]:
    """Creates tables; seeds only an empty store; never logs an upload."""
    conn = cs.get_connection(str(db_path))
    try:
        cs.init_db(conn)
        if cs.get_all_patients(conn):
            return {"quarantined": []}
        try:
            seed_df = pd.read_csv(seed_csv)
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
    finally:
        conn.close()
