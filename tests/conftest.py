"""Shared fixtures. Nothing here touches the working directory."""

import json

import pandas as pd
import pytest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.models import Patient
from aarogya.m14_audit import logging_setup

SAMPLE_COLUMNS = [
    "patient_id",
    "name",
    "age",
    "gender",
    "bmi",
    "bp_systolic",
    "bp_diastolic",
    "sugar_fasting",
    "city",
]

# Use distinctive names for leak checks
SAMPLE_ROWS = [
    [
        "P001",
        "Zarina Synthetic",
        34,
        "Female",
        22.4,
        118,
        76,
        92,
        "Chennai",
    ],
    ["P002", "Kiran Fabricated", 58, "Male", 31.2, 152, 96, 141, "Delhi"],
    ["P003", "Meera Placeholder", 45, "Female", 27.9, 134, 84, 118, "Pune"],
    ["P004", "Rohan Mockperson", 29, "Male", 19.8, 112, 72, 86, "Mumbai"],
]


@pytest.fixture
def make_patient():
    def _make(pid="P1", bmi=24.0, sbp=120.0):
        return Patient(pid, "Test", 40, "M", bmi, sbp, 80.0, 90.0, "Delhi")

    return _make


@pytest.fixture
def db():
    conn = cs.get_connection(":memory:")
    cs.init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def db_file(tmp_path):
    path = tmp_path / "aarogya.db"
    conn = cs.get_connection(str(path))
    cs.init_db(conn)
    conn.close()
    return path


@pytest.fixture
def sample_df():
    return pd.DataFrame(SAMPLE_ROWS, columns=SAMPLE_COLUMNS)


@pytest.fixture
def sample_csv(tmp_path, sample_df):
    path = tmp_path / "patients_sample.csv"
    sample_df.to_csv(path, index=False)
    return path


@pytest.fixture
def log_file(tmp_path):
    path = tmp_path / "logs" / "aarogya.log"
    logging_setup.configure_logging(path)
    yield path
    logging_setup.shutdown_logging()


@pytest.fixture
def read_log():
    def _read(path):
        with open(path, encoding="utf-8") as handle:
            return [json.loads(ln) for ln in handle if ln.strip()]

    return _read
