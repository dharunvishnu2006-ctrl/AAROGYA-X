"""The API server must never print a request line (holds patient_id)."""

import logging
import threading
import urllib.request

import pytest
from flask import Flask
from werkzeug.serving import WSGIRequestHandler, make_server

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m14_audit.logging_setup import shutdown_logging
from aarogya.platform import api, paths


@pytest.fixture
def store(db_file, sample_df):
    conn = cs.get_connection(str(db_file))
    ingest_dataframe(conn, sample_df)
    conn.close()
    return db_file


def _serve_once(store, handler, path):
    # Serve one request on loopback only
    server = make_server(
        api.HOST, 0, api.create_app(store), request_handler=handler
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://{api.HOST}:{server.server_port}{path}"
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.status == 200
    finally:
        server.shutdown()
        thread.join(timeout=10)
        server.server_close()


def _werkzeug_text(caplog):
    return " ".join(
        r.getMessage() for r in caplog.records if r.name == "werkzeug"
    )


def test_default_handler_would_leak_patient_id(store, caplog):
    # Prove capture works with stock handler
    caplog.set_level(logging.INFO, logger="werkzeug")
    _serve_once(store, WSGIRequestHandler, "/patients/P001")
    assert "/patients/P001" in _werkzeug_text(caplog)


def test_quiet_handler_prints_no_request_line(store, caplog, capfd):
    caplog.set_level(logging.DEBUG, logger="werkzeug")
    _serve_once(store, api.QuietRequestHandler, "/patients/P001")
    assert "P001" not in _werkzeug_text(caplog)
    out, err = capfd.readouterr()
    assert "P001" not in out and "P001" not in err


def test_quiet_handler_drops_error_lines_too(caplog):
    caplog.set_level(logging.DEBUG, logger="werkzeug")
    handler = api.QuietRequestHandler.__new__(api.QuietRequestHandler)
    handler.log_error("code %d, bad line %r", 400, "GET /patients/P007")
    handler.log_message("%s", "GET /patients/P007")
    assert _werkzeug_text(caplog) == ""


def test_main_runs_with_quiet_handler(monkeypatch, tmp_path):
    seen = {}

    def fake_run(self, **options):
        seen.update(options)

    monkeypatch.setattr(Flask, "run", fake_run)
    monkeypatch.setattr(paths, "LOG_FILE", tmp_path / "logs" / "a.log")
    try:
        api.main()
    finally:
        shutdown_logging()
    assert seen["request_handler"] is api.QuietRequestHandler
    assert seen["host"] == "127.0.0.1"
    assert seen["debug"] is False
