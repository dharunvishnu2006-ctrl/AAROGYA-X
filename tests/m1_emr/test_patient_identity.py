import pytest

from aarogya.m1_emr import models
from aarogya.m1_emr.models import Patient

HIGH = dict(bmi=32.0, bp_systolic=150, bp_diastolic=95, sugar_fasting=140)
MEDIUM = dict(bmi=32.0, bp_systolic=120, bp_diastolic=80, sugar_fasting=90)
LOW = dict(bmi=22.0, bp_systolic=120, bp_diastolic=80, sugar_fasting=90)


def make(pid, name="Pushti Jain", vitals=LOW):
    return Patient(
        patient_id=pid,
        name=name,
        age=40,
        gender="F",
        city="Pune",
        **vitals,
    )


def test_same_id_different_name_is_equal():
    a, b = make("P007"), make("P007", name="Someone Else")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_same_details_different_id_not_equal():
    a, b = make("P007"), make("P031")
    assert a != b
    assert len({a, b}) == 2


def test_not_equal_to_non_patient():
    assert make("P007") != "P007"


def test_str_shows_id_and_initial_only():
    p = make("P007", vitals=HIGH)
    assert str(p) == "P007 · Pushti J."
    for text in (str(p), repr(p)):
        for vital in ("32", "150", "95", "140", "40"):
            assert vital not in text


def test_str_single_word_name():
    assert str(make("P007", name="Pushti")) == "P007 · Pushti"


def test_sorted_gives_triage_order():
    low, med, high = (
        make("P001"),
        make("P002", vitals=MEDIUM),
        make("P003", vitals=HIGH),
    )
    assert sorted([low, med, high]) == [high, med, low]


def test_ties_sorted_by_numeric_id():
    later, earlier = make("P1000"), make("P999")
    assert [p.patient_id for p in sorted([later, earlier])] == [
        "P999",
        "P1000",
    ]


def test_patient_id_is_read_only():
    p = make("P007")
    with pytest.raises(AttributeError):
        p.patient_id = "P008"  # type: ignore[misc]


def test_doctor_removed():
    assert not hasattr(models, "Doctor")
