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


def test_hospitals_and_stays_tables_created(db):
    cols = {
        table: [r[1] for r in db.execute(f"PRAGMA table_info({table})")]
        for table in ("hospitals", "stays")
    }
    assert cols["hospitals"] == [
        "hospital_id",
        "name",
        "city",
        "total_beds",
    ]
    assert cols["stays"] == [
        "stay_id",
        "patient_id",
        "hospital_id",
        "ward",
        "bed",
        "admitted_at",
        "discharged_at",
    ]


def test_stays_schema_has_no_check_or_index(db):
    # Keep stay rules in stays.py only
    sql = db.execute(
        "SELECT sql FROM sqlite_master WHERE name = 'stays'"
    ).fetchone()[0]
    assert "CHECK" not in sql.upper()
    indexes = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' "
        "AND tbl_name = 'stays' AND sql IS NOT NULL"
    ).fetchall()
    assert indexes == []


def test_init_db_upgrades_old_store_keeping_patients(
    tmp_path, make_patient
):
    path = str(tmp_path / "old.db")
    conn = cs.get_connection(path)
    cs.init_db(conn)
    cs.insert_patient(conn, make_patient("P001"))
    conn.execute("DROP TABLE stays")
    conn.execute("DROP TABLE hospitals")
    conn.commit()
    cs.init_db(conn)
    assert cs.count_patients(conn) == 1
    assert conn.execute("SELECT COUNT(*) FROM stays").fetchone()[0] == 0
    conn.close()


def test_stays_foreign_keys_enforced(db, make_patient):
    cs.insert_patient(db, make_patient("P001"))
    db.execute("INSERT INTO hospitals VALUES ('H001', 'A', 'Delhi', 5)")
    insert = (
        "INSERT INTO stays (patient_id, hospital_id, ward, bed, "
        "admitted_at) VALUES (?, ?, 'W', 'B', '2026-09-01T00:00:00+00:00')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, ("P999", "H001"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, ("P001", "H999"))


def test_readonly_connection_cannot_write_or_create(tmp_path, db_file):
    conn = cs.get_readonly_connection(str(db_file))
    try:
        assert cs.count_patients(conn) == 0
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM patients")
    finally:
        conn.close()
    missing = tmp_path / "missing.db"
    with pytest.raises(sqlite3.OperationalError):
        cs.get_readonly_connection(str(missing))
    assert not missing.exists()
