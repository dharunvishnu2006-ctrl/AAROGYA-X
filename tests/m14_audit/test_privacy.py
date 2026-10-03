"""No log line may hold a patient name, patient_id or vital value."""

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m14_audit.logging_setup import ALLOWED_FIELDS, log_error
from aarogya.m14_audit.logging_setup import log_event

BASE_KEYS = {"time", "level", "event", "module", "run_id"}
SKIP_KEYS = {"time", "run_id"}


def _exercise_every_event(tmp_path, sample_csv, sample_df):
    db_path = tmp_path / "aarogya.db"
    log_event("app_start", "app")
    bootstrap_store(db_path, sample_csv)
    conn = cs.get_connection(str(db_path))
    try:
        upload = sample_df.copy()
        upload["patient_id"] = ["P101", "P102", "P103", "P104"]
        upload.loc[2, "sugar_fasting"] = 900
        result = ingest_dataframe(conn, upload)
        cs.record_ingest(
            conn, result.rows_read, result.accepted, result.rejected
        )
        log_event(
            "upload",
            "m1_emr",
            rows_read=result.rows_read,
            accepted=result.accepted,
            rejected=result.rejected,
        )
        cs.correct_patient_vital(conn, "P001", "bmi", 23.7, "Re-weighed")
        log_event("correction_saved", "m1_emr")
        try:
            cs.correct_patient_vital(conn, "P999", "bmi", 23.7, "Typo")
        except KeyError as err:
            log_error("m1_emr", err)
        try:
            cs.correct_patient_vital(conn, "P002", "bmi", 4.0, "Typo")
        except ValueError as err:
            log_error("m1_emr", err)
    finally:
        conn.close()


def test_log_has_no_patient_data(
    tmp_path, sample_csv, sample_df, log_file, read_log
):
    _exercise_every_event(tmp_path, sample_csv, sample_df)
    lines = read_log(log_file)
    events = [line["event"] for line in lines]
    assert events == [
        "app_start",
        "seed_loaded",
        "upload",
        "correction_saved",
        "error",
        "error",
    ]
    assert lines[2]["rows_read"] == 4
    assert lines[2]["accepted"] == 3
    assert lines[2]["rejected"] == 1
    for line in lines:
        assert set(line) <= BASE_KEYS | ALLOWED_FIELDS
    # Exclude time and run_id; digits collide
    body = " ".join(
        str(v)
        for line in lines
        for k, v in line.items()
        if k not in SKIP_KEYS
    )
    assert "P0" not in body and "P1" not in body and "P9" not in body
    for name in sample_df["name"]:
        for part in name.split():
            assert part not in body
    # Allow only counts and known labels
    for line in lines:
        assert line["level"] in {"INFO", "ERROR"}
        assert line["module"] in {"app", "m1_emr"}
        assert line.get("error_type") in {None, "KeyError", "ValueError"}
        for key in ("rows_read", "accepted", "rejected"):
            if key in line:
                assert type(line[key]) is int
                assert 0 <= line[key] <= len(sample_df)
