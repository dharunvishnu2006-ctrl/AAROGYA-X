"""M2 fixtures: a store with sample patients and small hospitals."""

import pytest

from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m2_his.hospitals import Hospital, insert_hospital

# Keep bed counts small for maths
SMALL_HOSPITALS = [
    Hospital("H001", "Test Chennai", "Chennai", 4),
    Hospital("H002", "Test Delhi", "Delhi", 2),
    Hospital("H003", "Test Pune", "Pune", 0),
]


@pytest.fixture
def his_db(db, sample_df):
    ingest_dataframe(db, sample_df)
    for hospital in SMALL_HOSPITALS:
        insert_hospital(db, hospital)
    return db


@pytest.fixture
def at():
    def _at(day, hour=8):
        return f"2026-09-{day:02d}T{hour:02d}:00:00+00:00"

    return _at
