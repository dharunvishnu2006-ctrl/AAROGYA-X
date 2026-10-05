import numpy as np
import pytest

from aarogya.m1_emr.models import Patient


@pytest.fixture
def patient():
    return Patient(
        "P007", "Pushti Jain", 40, "F", 24.0, 130, 85, 100, "Pune"
    )


def test_negative_age_rejected(patient):
    with pytest.raises(ValueError):
        patient.age = -5


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", 126),
        ("bmi", 5.0),
        ("bmi", 95.0),
        ("bp_systolic", 40),
        ("bp_systolic", 310),
        ("bp_diastolic", 20),
        ("bp_diastolic", 210),
        ("sugar_fasting", 10),
        ("sugar_fasting", 800),
        ("bmi", "abc"),
    ],
)
def test_impossible_value_rejected(patient, field, value):
    with pytest.raises(ValueError):
        setattr(patient, field, value)


@pytest.mark.parametrize(
    "field,value", [("bp_systolic", 85), ("bp_diastolic", 130)]
)
def test_systolic_not_above_diastolic_rejected(patient, field, value):
    with pytest.raises(ValueError):
        setattr(patient, field, value)


def test_failed_set_keeps_old_value(patient):
    with pytest.raises(ValueError):
        patient.bmi = 5.0
    assert patient.bmi == 24.0


def test_valid_set_and_numpy_coercion(patient):
    patient.age = np.int64(41)
    patient.bp_systolic = np.float64(140)
    assert isinstance(patient.age, int) and patient.age == 41
    assert isinstance(patient.bp_systolic, float)
    assert patient.bp_systolic == 140.0
