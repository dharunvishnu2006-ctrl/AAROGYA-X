import sqlite3

import pytest
from aarogya.m1_emr import clinical_store as cs


def test_schema_init(db):
    tables = {
        r[0]
        for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"patients", "patient_corrections"}.issubset(tables)


def test_insert_and_duplicate_reject(db, make_patient):
    p = make_patient()
    cs.insert_patient(db, p)
    assert cs.get_patient(db, "P001")["name"] == "Test"
    with pytest.raises(sqlite3.IntegrityError):
        cs.insert_patient(db, p)


def test_correction_and_audit(db, make_patient):
    cs.insert_patient(db, make_patient())
    cs.correct_patient_vital(db, "P001", "bmi", 26.5, "Weight increase")
    assert cs.get_patient(db, "P001")["bmi"] == 26.5
    history = cs.get_patient_history(db, "P001")
    assert len(history) == 1
    assert (
        history[0]["old_value"] == "24.0"
        and history[0]["new_value"] == "26.5"
    )


def test_correction_guards(db, make_patient):
    cs.insert_patient(db, make_patient())
    with pytest.raises(ValueError, match="already"):
        cs.correct_patient_vital(db, "P001", "bmi", 24.0, "No change")
    with pytest.raises(ValueError, match="justification"):
        cs.correct_patient_vital(db, "P001", "bmi", 25.0, "   ")
    with pytest.raises(ValueError, match="editable"):
        cs.correct_patient_vital(db, "P001", "name", "New", "Valid reason")
    with pytest.raises(KeyError):
        cs.correct_patient_vital(db, "P99", "bmi", 25.0, "Valid reason")


def test_disk_persistence(tmp_path, make_patient):
    f = str(tmp_path / "test.db")
    c1 = cs.get_connection(f)
    cs.init_db(c1)
    cs.insert_patient(c1, make_patient())
    c1.close()

    c2 = cs.get_connection(f)
    assert cs.get_patient(c2, "P001") is not None
    c2.close()


def test_ingest_log_table_created(db):
    tables = {
        r[0]
        for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "ingest_log" in tables


def test_record_ingest_appends_never_overwrites(db):
    assert cs.get_last_ingest_utc(db) is None
    cs.record_ingest(db, 10, 8, 2)
    cs.record_ingest(db, 5, 5, 0)
    log = cs.get_ingest_log(db)
    assert [
        (r["rows_read"], r["accepted"], r["rejected"]) for r in log
    ] == [(10, 8, 2), (5, 5, 0)]
    assert cs.get_last_ingest_utc(db) == log[-1]["recorded_at"]


def test_ingest_log_has_no_patient_columns(db):
    cols = {r[1] for r in db.execute("PRAGMA table_info(ingest_log)")}
    assert cols == {
        "id",
        "recorded_at",
        "rows_read",
        "accepted",
        "rejected",
    }


def test_count_patients(db, make_patient):
    assert cs.count_patients(db) == 0
    cs.insert_patient(db, make_patient("P001"))
    cs.insert_patient(db, make_patient("P002"))
    assert cs.count_patients(db) == 2


def test_stored_timestamps_are_utc(db, make_patient):
    cs.insert_patient(db, make_patient())
    assert cs.get_patient(db, "P001")["updated_at"].endswith("+00:00")
    cs.correct_patient_vital(db, "P001", "bmi", 26.0, "Re-measured")
    assert cs.get_patient(db, "P001")["updated_at"].endswith("+00:00")
    history = cs.get_patient_history(db, "P001")
    assert history[0]["recorded_at"].endswith("+00:00")
    cs.record_ingest(db, 1, 1, 0)
    assert cs.get_last_ingest_utc(db).endswith("+00:00")
