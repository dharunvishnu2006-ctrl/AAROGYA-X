import numpy as np
import pytest
from aarogya.m1_emr.models import Patient


def test_valid_patient():
    p = Patient("P101", "Aarav", 35, "Male", 24.5, 120, 80, 95, "Delhi")
    assert p.age == 35 and p.gender == "M" and p.bp_systolic == 120.0


@pytest.mark.parametrize("age", [-1, 135])
def test_invalid_age(age):
    with pytest.raises(ValueError):
        Patient("P102", "Dev", age, "M", 22.0, 120, 80, 90, "Delhi")


@pytest.mark.parametrize("gender", ["Alien", "X"])
def test_invalid_gender(gender):
    with pytest.raises(ValueError):
        Patient("P103", "Dev", 30, gender, 22.0, 120, 80, 90, "Delhi")


@pytest.mark.parametrize(
    "bmi,sugar", [(5.0, 90), (110.0, 90), (22.0, 15.0)]
)
def test_implausible_vitals(bmi, sugar):
    with pytest.raises(ValueError):
        Patient("P104", "Dev", 30, "M", bmi, 120, 80, sugar, "Delhi")


@pytest.mark.parametrize("sys,dia", [(107, 107), (104, 109)])
def test_systolic_le_diastolic(sys, dia):
    with pytest.raises(ValueError):
        Patient("P105", "Dev", 30, "M", 22.0, sys, dia, 90, "Delhi")


def test_numpy_int64_coercion():
    p = Patient(
        "P106",
        "Dev",
        np.int64(71),
        "F",
        np.float64(24.5),
        130,
        85,
        100,
        "Delhi",
    )
    assert isinstance(p.age, int) and p.age == 71
