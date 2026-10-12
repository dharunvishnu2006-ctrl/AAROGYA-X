from aarogya.m6_risk.cohort_stats import describe_vitals
from aarogya.m6_risk.scoring import HasVitals, ThresholdRiskScorer

# Share one stateless scorer instance
_DEFAULT_SCORER = ThresholdRiskScorer()


def calc_avg_bmi(df):
    """Kept for old callers; reads from cohort_stats."""
    bmi = describe_vitals(df).loc["bmi"]
    return {
        "mean": round(bmi["mean"], 2),
        "min": round(bmi["min"], 2),
        "max": round(bmi["max"], 2),
    }


def score_patient_risk(patient: HasVitals) -> str:
    """Delegates to the threshold scorer; results unchanged."""
    return _DEFAULT_SCORER.score(patient)
