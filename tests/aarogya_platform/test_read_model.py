import pandas as pd
import pytest

from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m6_risk.cohort_stats import (
    AGE_BAND_LABELS,
    add_age_band,
    describe_vitals,
)
from aarogya.platform import read_model


@pytest.fixture
def filled(db, sample_df):
    ingest_dataframe(db, sample_df)
    return db


@pytest.mark.parametrize("age", [0, 18, 29, 30, 44, 45, 59, 60, 120])
def test_age_band_of_matches_add_age_band(age):
    frame = add_age_band(pd.DataFrame({"age": [age]}))
    assert read_model.age_band_of(age) == str(frame["age_band"][0])
    assert read_model.age_band_of(age) in AGE_BAND_LABELS


@pytest.mark.parametrize("pid", ["P001", "P1234"])
def test_valid_patient_ids(pid):
    assert read_model.is_valid_patient_id(pid)


@pytest.mark.parametrize("pid", ["PX01", "P01", "p001", "P001 ", "001"])
def test_invalid_patient_ids(pid):
    assert not read_model.is_valid_patient_id(pid)


def test_patient_view_has_no_name(filled, sample_df):
    view = read_model.patient_view(filled, "P001")
    assert set(view) == {"patient_id", "age_band", "city", "vitals", "risk"}
    assert view["patient_id"] == "P001"
    assert view["age_band"] == "30-44"
    assert view["city"] == "Chennai"
    assert view["vitals"] == {
        "bmi": 22.4,
        "bp_systolic": 118.0,
        "bp_diastolic": 76.0,
        "sugar_fasting": 92.0,
    }
    assert view["risk"] in {"Low", "Medium", "High"}
    text = str(view)
    for part in sample_df.loc[0, "name"].split():
        assert part not in text


def test_patient_view_unknown_is_none(filled):
    assert read_model.patient_view(filled, "P999") is None


def test_cohort_summary_matches_cohort_stats(filled, sample_df):
    summary = read_model.cohort_summary(filled)
    expected = describe_vitals(sample_df)
    assert summary["cohort_size"] == 4
    for vital in expected.index:
        for stat, value in expected.loc[vital].items():
            assert summary["vitals"][vital][stat] == pytest.approx(value)
    assert type(summary["vitals"]["bmi"]["count"]) is int


def test_cohort_summary_single_patient_std_is_none(db, sample_df):
    ingest_dataframe(db, sample_df.iloc[[0]])
    summary = read_model.cohort_summary(db)
    assert summary["vitals"]["bmi"]["std"] is None


def test_cohort_summary_empty_store(db):
    assert read_model.cohort_summary(db) == {"cohort_size": 0, "vitals": {}}
