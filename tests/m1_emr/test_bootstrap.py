import os

import pandas as pd

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m14_audit.health import health
from aarogya.m2_his import hospitals, stays


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


def test_seed_with_bom_and_spaced_header(tmp_path, sample_df):
    seed = tmp_path / "seed.csv"
    spaced = sample_df.rename(columns=lambda c: f" {c} ")
    spaced.to_csv(seed, index=False, encoding="utf-8-sig")
    db_path = tmp_path / "aarogya.db"
    assert bootstrap_store(db_path, seed) == {"quarantined": []}
    assert health(db_path)["patient_count"] == 4


def _his_csvs(tmp_path):
    hospitals_csv = tmp_path / "hospitals.csv"
    hospitals_csv.write_text(
        "hospital_id,name,city,total_beds\nH001,A,Chennai,4\n",
        encoding="utf-8",
    )
    stays_csv = tmp_path / "stays.csv"
    stays_csv.write_text(
        "patient_id,hospital_id,ward,bed,admitted_at,discharged_at\n"
        "P001,H001,General,B01,2026-09-01T08:00:00+00:00,\n"
        "P001,H001,General,B02,2026-09-02T08:00:00+00:00,\n",
        encoding="utf-8",
    )
    return hospitals_csv, stays_csv


def test_first_start_seeds_hospitals_and_stays(
    tmp_path, sample_csv, log_file, read_log
):
    db_path = tmp_path / "aarogya.db"
    status = bootstrap_store(db_path, sample_csv, *_his_csvs(tmp_path))
    assert status == {"quarantined": []}
    conn = cs.get_connection(str(db_path))
    try:
        assert hospitals.count_hospitals(conn) == 1
        assert stays.count_stays(conn) == 1
    finally:
        conn.close()
    lines = {line["event"]: line for line in read_log(log_file)}
    assert lines["hospitals_loaded"]["accepted"] == 1
    assert lines["stays_loaded"]["rows_read"] == 2
    assert lines["stays_loaded"]["accepted"] == 1
    assert lines["stays_loaded"]["rejected"] == 1
    assert lines["stays_loaded"]["module"] == "m2_his"


def test_restart_does_not_reseed_stays(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    his = _his_csvs(tmp_path)
    bootstrap_store(db_path, sample_csv, *his)
    bootstrap_store(db_path, sample_csv, *his)
    conn = cs.get_connection(str(db_path))
    try:
        assert hospitals.count_hospitals(conn) == 1
        assert stays.count_stays(conn) == 1
    finally:
        conn.close()


def test_existing_patients_still_get_stays(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(db_path, sample_csv)
    bootstrap_store(db_path, sample_csv, *_his_csvs(tmp_path))
    conn = cs.get_connection(str(db_path))
    try:
        assert stays.count_stays(conn) == 1
    finally:
        conn.close()


def test_missing_his_csvs_are_skipped(tmp_path, sample_csv):
    db_path = tmp_path / "aarogya.db"
    status = bootstrap_store(
        db_path, sample_csv, tmp_path / "no_h.csv", tmp_path / "no_s.csv"
    )
    assert status == {"quarantined": []}
    assert health(db_path)["patient_count"] == 4
