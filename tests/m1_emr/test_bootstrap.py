import os

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m14_audit.health import health


def test_first_start_creates_and_seeds(tmp_path, sample_csv):
    db_path = tmp_path / "fresh" / "aarogya.db"
    db_path.parent.mkdir()
    assert not db_path.exists()
    status = bootstrap_store(db_path, sample_csv)
    assert db_path.exists()
    assert status == {"quarantined": []}
    report = health(db_path)
    assert report["status"] == "healthy"
    assert report["store_reachable"] is True
    assert report["patient_count"] == 4
    assert report["last_upload_utc"] is None


def test_seed_is_not_an_upload(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(db_path, sample_csv)
    conn = cs.get_connection(str(db_path))
    try:
        assert cs.get_ingest_log(conn) == []
    finally:
        conn.close()


def test_restart_does_not_reseed(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(db_path, sample_csv)
    bootstrap_store(db_path, sample_csv)
    assert health(db_path)["patient_count"] == 4


def test_missing_seed_csv_gives_empty_healthy_store(tmp_path):
    db_path = tmp_path / "aarogya.db"
    status = bootstrap_store(db_path, tmp_path / "no_such.csv")
    assert status == {"quarantined": []}
    report = health(db_path)
    assert report["status"] == "healthy"
    assert report["patient_count"] == 0


def test_seed_quarantines_invalid_rows(tmp_path, sample_df):
    sample_df.loc[0, "bp_systolic"] = 60
    csv_path = tmp_path / "seed.csv"
    sample_df.to_csv(csv_path, index=False)
    status = bootstrap_store(tmp_path / "aarogya.db", csv_path)
    assert [q["id"] for q in status["quarantined"]] == ["P001"]
    assert health(tmp_path / "aarogya.db")["patient_count"] == 3


def test_seed_duplicate_quarantined_and_rejected(
    tmp_path, sample_df, log_file, read_log
):
    dup = sample_df.iloc[[0]].assign(name="Second Copy", bmi=35.0)
    seed = pd.concat([sample_df, dup], ignore_index=True)
    csv_path = tmp_path / "seed.csv"
    seed.to_csv(csv_path, index=False)
    db_path = tmp_path / "aarogya.db"
    status = bootstrap_store(db_path, csv_path)
    assert status == {
        "quarantined": [
            {"row": 5, "id": "P001", "reason": "duplicate patient_id"}
        ]
    }
    assert health(db_path)["patient_count"] == 4
    conn = cs.get_connection(str(db_path))
    try:
        first = cs.get_patient(conn, "P001")
        assert first["name"] == "Zarina Synthetic"
        assert first["bmi"] == 22.4
        assert cs.get_patient_history(conn, "P001") == []
    finally:
        conn.close()
    seed_line = read_log(log_file)[0]
    assert seed_line["event"] == "seed_loaded"
    assert seed_line["rows_read"] == 5
    assert seed_line["accepted"] == 4
    assert seed_line["rejected"] == 1


def test_store_removed_after_bootstrap_is_unhealthy(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(db_path, sample_csv)
    os.rename(db_path, tmp_path / "aarogya.db.moved")
    report = health(db_path)
    assert report["status"] == "unhealthy"
    assert report["store_reachable"] is False
    assert not db_path.exists()
