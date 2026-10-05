"""Risk scoring as a strategy: one interface, swappable rules."""

from abc import ABC, abstractmethod
from typing import Protocol

from aarogya.m6_risk.clinical_config import (
    BMI_OBESITY,
    BP_DIASTOLIC_HIGH,
    BP_SYSTOLIC_HIGH,
    FASTING_SUGAR_DIABETES,
)

# Rank bands for triage; High first
RISK_RANK = {"High": 0, "Medium": 1, "Low": 2}


class HasVitals(Protocol):
    bmi: float
    bp_systolic: float
    bp_diastolic: float
    sugar_fasting: float


class RiskScorer(ABC):
    @abstractmethod
    def score(self, patient: HasVitals) -> str:
        """Returns the band: "Low", "Medium" or "High"."""


class ThresholdRiskScorer(RiskScorer):
    """Counts guideline breaches: 0 Low, 1 Medium, 2+ High."""

    def score(self, patient: HasVitals) -> str:
        risk_score = 0

        if patient.bmi >= BMI_OBESITY.value:
            risk_score += 1

        if (
            patient.bp_systolic >= BP_SYSTOLIC_HIGH.value
            or patient.bp_diastolic >= BP_DIASTOLIC_HIGH.value
        ):
            risk_score += 1

        if patient.sugar_fasting >= FASTING_SUGAR_DIABETES.value:
            risk_score += 1

        if risk_score == 0:
            return "Low"
        elif risk_score == 1:
            return "Medium"
        else:
            return "High"
