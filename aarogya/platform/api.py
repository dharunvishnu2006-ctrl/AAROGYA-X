"""Read-only JSON API over the clinical store; localhost only.

Routes are thin: parse, validate, call one read_model function,
return JSON. Any failure below a route becomes a 503, never a 500.
No authentication yet, so the server binds 127.0.0.1 only.
Usage: python -m aarogya.platform.api
"""

import json
from pathlib import Path
from typing import Any, Callable, Union

from flask import Flask, Response, jsonify
from werkzeug.exceptions import HTTPException
from werkzeug.serving import WSGIRequestHandler

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE
from aarogya.m14_audit.health import health
from aarogya.m14_audit.logging_setup import configure_logging, log_error
from aarogya.platform import paths, read_model

HOST = "127.0.0.1"
PORT = 5000
API_MODULE = "platform"
NOT_FOUND_MESSAGE = "Patient not found."
STORE_ERROR_MESSAGE = "Data store unavailable."
FHIR_MIMETYPE = "application/fhir+json"


class QuietRequestHandler(WSGIRequestHandler):
    """Drops werkzeug's per-request lines.

    A request line holds the URL path, e.g. /patients/P007, so it
    must never reach the terminal. Startup messages use werkzeug's
    module logger, not this method, so they still print.
    """

    def log(self, type: str, message: str, *args: Any) -> None:
        return None


def create_app(db_path: Union[str, Path] = paths.DB_PATH) -> Flask:
    """Builds the API for one store; GET routes only."""
    app = Flask(__name__)

    def read(view: Callable[..., Any], *args: Any) -> Any:
        conn = cs.get_readonly_connection(str(db_path))
        try:
            return view(conn, *args)
        finally:
            conn.close()

    @app.errorhandler(Exception)
    def on_error(err: Exception) -> Any:
        if isinstance(err, HTTPException):
            return jsonify(error=err.description), err.code
        # Log class name only, never data
        log_error(API_MODULE, err)
        return jsonify(error=STORE_ERROR_MESSAGE), 503

    @app.get("/health")
    def get_health() -> Any:
        report = health(db_path)
        code = 200 if report["status"] == "healthy" else 503
        return jsonify(report), code

    @app.get("/cohort/stats")
    def get_cohort_stats() -> Any:
        return jsonify(read(read_model.cohort_summary))

    @app.get("/patients/<patient_id>")
    def get_patient(patient_id: str) -> Any:
        if not read_model.is_valid_patient_id(patient_id):
            return jsonify(error=PATIENT_ID_FORMAT_MESSAGE), 400
        view = read(read_model.patient_view, patient_id)
        if view is None:
            return jsonify(error=NOT_FOUND_MESSAGE), 404
        return jsonify(view)

    @app.get("/patients/<patient_id>/fhir")
    def get_patient_fhir(patient_id: str) -> Any:
        if not read_model.is_valid_patient_id(patient_id):
            return jsonify(error=PATIENT_ID_FORMAT_MESSAGE), 400
        bundle = read(read_model.patient_fhir, patient_id)
        if bundle is None:
            return jsonify(error=NOT_FOUND_MESSAGE), 404
        return Response(json.dumps(bundle), mimetype=FHIR_MIMETYPE)

    @app.get("/hospitals/occupancy")
    def get_occupancy() -> Any:
        return jsonify(read(read_model.occupancy_view))

    return app


def main() -> None:
    configure_logging(paths.LOG_FILE)
    create_app().run(
        host=HOST,
        port=PORT,
        debug=False,
        request_handler=QuietRequestHandler,
    )


if __name__ == "__main__":
    main()
