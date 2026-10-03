import logging
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import pytest

from aarogya.m14_audit import logging_setup as ls

FIELDS = {"time", "level", "event", "module", "run_id"}


def test_lines_are_json_with_required_fields(log_file, read_log):
    ls.log_event("app_start", "app")
    ls.log_event("upload", "m1_emr", rows_read=5, accepted=4, rejected=1)
    lines = read_log(log_file)
    assert len(lines) == 2
    assert FIELDS <= set(lines[0])
    assert lines[0]["event"] == "app_start"
    assert lines[0]["level"] == "INFO"
    assert lines[0]["module"] == "app"
    assert lines[1]["rows_read"] == 5
    assert lines[1]["accepted"] == 4
    assert lines[1]["rejected"] == 1


def test_time_is_utc_iso8601(log_file, read_log):
    ls.log_event("app_start", "app")
    stamp = read_log(log_file)[0]["time"]
    parsed = datetime.fromisoformat(stamp)
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)
    assert stamp.endswith("+00:00")


def test_run_id_is_stable_uuid(log_file, read_log):
    ls.log_event("app_start", "app")
    ls.log_event("correction_saved", "m1_emr")
    run_ids = {line["run_id"] for line in read_log(log_file)}
    assert run_ids == {ls.RUN_ID}
    assert uuid.UUID(ls.RUN_ID).version == 4


def test_file_is_utf8_and_rotating(log_file):
    ls.log_event("app_start", "módulo")
    raw = log_file.read_bytes()
    assert "módulo".encode("utf-8") in raw
    handlers = logging.getLogger(ls.LOGGER_NAME).handlers
    assert len(handlers) == 1
    assert isinstance(handlers[0], RotatingFileHandler)
    assert handlers[0].encoding == "utf-8"
    assert handlers[0].maxBytes > 0 and handlers[0].backupCount > 0


def test_configure_twice_no_duplicate_lines(log_file, read_log):
    ls.configure_logging(log_file)
    ls.log_event("app_start", "app")
    assert len(read_log(log_file)) == 1


def test_configure_creates_log_folder(tmp_path):
    target = tmp_path / "new" / "deeper" / "aarogya.log"
    try:
        ls.configure_logging(target)
        ls.log_event("app_start", "app")
        assert target.is_file()
    finally:
        ls.shutdown_logging()


def test_error_logs_class_name_only(log_file, read_log):
    ls.log_error("m1_emr", KeyError("Patient with ID 'P001' not found."))
    line = read_log(log_file)[0]
    assert line["level"] == "ERROR"
    assert line["event"] == "error"
    assert line["error_type"] == "KeyError"
    assert "P001" not in log_file.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "fields",
    [
        {"patient_id": "P001"},
        {"name": "Zarina Synthetic"},
        {"bmi": 22.4},
        {"rows_read": "P001"},
        {"accepted": 2.5},
        {"rejected": True},
        {"error_type": "BMI 5.0 is implausible"},
    ],
)
def test_disallowed_fields_raise(log_file, fields):
    with pytest.raises(ValueError):
        ls.log_event("upload", "m1_emr", **fields)
    assert not log_file.exists() or log_file.read_text() == ""


def test_unknown_event_raises(log_file):
    with pytest.raises(ValueError, match="Unknown log event"):
        ls.log_event("Patient P001 admitted", "m1_emr")
