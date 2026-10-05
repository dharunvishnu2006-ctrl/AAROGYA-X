import sqlite3

from aarogya.m1_emr import clinical_store as cs
from aarogya.m14_audit.health import health

KEYS = {"status", "store_reachable", "patient_count", "last_upload_utc"}


def test_healthy_store(db_file):
    report = health(db_file)
    assert set(report) == KEYS
    assert report["status"] == "healthy"
    assert report["store_reachable"] is True
    assert report["patient_count"] == 0
    assert report["last_upload_utc"] is None


def test_count_is_live(db_file, make_patient):
    assert health(db_file)["patient_count"] == 0
    conn = cs.get_connection(str(db_file))
    cs.insert_patient(conn, make_patient("P001"))
    conn.close()
    assert health(db_file)["patient_count"] == 1


def test_last_upload_set_after_record_ingest(db_file):
    conn = cs.get_connection(str(db_file))
    cs.record_ingest(conn, 3, 2, 1)
    expected = cs.get_last_ingest_utc(conn)
    conn.close()
    assert health(db_file)["last_upload_utc"] == expected
    assert expected.endswith("+00:00")


def test_missing_file_unhealthy_and_not_created(tmp_path):
    missing = tmp_path / "gone.db"
    report = health(missing)
    assert report["status"] == "unhealthy"
    assert report["store_reachable"] is False
    assert report["patient_count"] is None
    assert not missing.exists()


def test_store_without_tables_unhealthy(tmp_path):
    path = tmp_path / "empty.db"
    sqlite3.connect(path).close()
    assert health(path)["status"] == "unhealthy"


def test_corrupt_file_unhealthy(tmp_path):
    path = tmp_path / "corrupt.db"
    path.write_bytes(b"this is not a sqlite database" * 100)
    assert health(path)["status"] == "unhealthy"


def test_store_older_than_ingest_log_unhealthy(tmp_path):
    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE patients (patient_id TEXT)")
    conn.close()
    assert health(path)["status"] == "unhealthy"
