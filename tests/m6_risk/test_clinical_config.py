from dataclasses import FrozenInstanceError
import pytest

from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.m6_risk.clinical_config import BP_SYSTOLIC_HIGH


class DummyPatient:
    def __init__(
        self,
        bmi: float,
        bp_systolic: float,
        bp_diastolic: float,
        sugar_fasting: float,
    ):
        self.bmi = bmi
        self.bp_systolic = bp_systolic
        self.bp_diastolic = bp_diastolic
        self.sugar_fasting = sugar_fasting


def test_clinical_thresholds_are_immutable():
    """Ensure clinical constants cannot be mutated at runtime."""
    with pytest.raises(FrozenInstanceError):
        BP_SYSTOLIC_HIGH.value = 130.0  # type: ignore


def test_score_patient_risk_normal_is_low():
    """All vitals strictly below thresholds -> 0 breaches -> Low risk."""
    patient = DummyPatient(
        bmi=22.0, bp_systolic=118.0, bp_diastolic=78.0, sugar_fasting=90.0
    )
    assert score_patient_risk(patient) == "Low"


def test_score_patient_risk_exact_clinical_boundaries_trigger_breaches():
    """Exact boundary values (BMI 30.0, BP 140/90, Sugar 126.0)
    must trigger inclusive breaches."""

    p_bmi = DummyPatient(
        bmi=30.0, bp_systolic=110.0, bp_diastolic=70.0, sugar_fasting=85.0
    )
    assert score_patient_risk(p_bmi) == "Medium"

    p_sys = DummyPatient(
        bmi=22.0, bp_systolic=140.0, bp_diastolic=75.0, sugar_fasting=85.0
    )
    assert score_patient_risk(p_sys) == "Medium"

    p_dia = DummyPatient(
        bmi=22.0, bp_systolic=120.0, bp_diastolic=90.0, sugar_fasting=85.0
    )
    assert score_patient_risk(p_dia) == "Medium"

    p_sug = DummyPatient(
        bmi=22.0, bp_systolic=120.0, bp_diastolic=80.0, sugar_fasting=126.0
    )
    assert score_patient_risk(p_sug) == "Medium"


def test_score_patient_risk_isolated_diastolic_triggers_bp_breach():
    """Isolated diastolic elevation (>90) with normal systolic (<140)
    triggers hypertension breach."""
    patient = DummyPatient(
        bmi=24.0, bp_systolic=122.0, bp_diastolic=94.0, sugar_fasting=95.0
    )
    assert score_patient_risk(patient) == "Medium"


def test_score_patient_risk_underweight_not_scored_as_metabolic_risk():
    """Underweight status (<18.5) must not increment metabolic score."""
    patient = DummyPatient(
        bmi=16.0, bp_systolic=110.0, bp_diastolic=70.0, sugar_fasting=80.0
    )
    assert score_patient_risk(patient) == "Low"


def test_score_patient_risk_multi_breach_high():
    """Obesity + high fasting sugar -> 2 breaches -> High risk."""
    patient = DummyPatient(
        bmi=32.5, bp_systolic=120.0, bp_diastolic=80.0, sugar_fasting=140.0
    )
    assert score_patient_risk(patient) == "High"
