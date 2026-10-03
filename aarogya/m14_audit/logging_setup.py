"""Structured JSON-lines logging with a per-process run_id.

Only fixed event names and allowlisted numeric fields can be logged,
so a patient name, patient_id or vital value cannot reach a log line.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union

from aarogya.platform import paths

LOGGER_NAME = "aarogya"
RUN_ID = uuid.uuid4().hex
MAX_BYTES = 1_000_000
BACKUP_COUNT = 5

EVENTS = frozenset(
    {"app_start", "seed_loaded", "upload", "correction_saved", "error"}
)
COUNT_FIELDS = frozenset({"rows_read", "accepted", "rejected"})
ALLOWED_FIELDS = COUNT_FIELDS | {"error_type"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        created = datetime.fromtimestamp(record.created, timezone.utc)
        payload = {
            "time": created.isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "unknown"),
            "module": getattr(record, "aarogya_module", "unknown"),
            "run_id": RUN_ID,
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    log_file: Union[str, Path] = paths.LOG_FILE,
) -> logging.Logger:
    """Attaches one rotating UTF-8 JSON handler; safe on every rerun."""
    logger = logging.getLogger(LOGGER_NAME)
    target = Path(log_file).resolve()
    for handler in list(logger.handlers):
        if Path(getattr(handler, "baseFilename", "")) == target:
            return logger
        logger.removeHandler(handler)
        handler.close()
    target.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        target,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def shutdown_logging() -> None:
    """Closes and detaches every aarogya handler."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def _check_fields(fields: dict) -> None:
    unknown = set(fields) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Disallowed log fields: {sorted(unknown)}")
    for key in COUNT_FIELDS & set(fields):
        value = fields[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Log field {key} must be an int count.")
    error_type = fields.get("error_type")
    if error_type is not None and not str(error_type).isidentifier():
        raise ValueError("Log field error_type must be a class name.")


def log_event(
    event: str, module: str, level: int = logging.INFO, **fields
) -> None:
    """Writes one structured event; rejects unknown events or fields."""
    if event not in EVENTS:
        raise ValueError(f"Unknown log event: {event}")
    _check_fields(fields)
    extra = {"event": event, "aarogya_module": module, "fields": fields}
    logging.getLogger(LOGGER_NAME).log(level, event, extra=extra)


def log_error(module: str, exc: BaseException) -> None:
    """Logs an exception's class name only, never its message."""
    log_event("error", module, logging.ERROR, error_type=type(exc).__name__)
