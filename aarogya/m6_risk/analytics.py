from aarogya.m6_risk.scoring import HasVitals, ThresholdRiskScorer

# Share one stateless scorer instance
_DEFAULT_SCORER = ThresholdRiskScorer()


def calc_avg_bmi(df):
    return {
        "mean": round(df["bmi"].mean(), 2),
        "min": round(df["bmi"].min(), 2),
        "max": round(df["bmi"].max(), 2),
    }


def calc_median_bp(df):
    return {
        "systolic_median": round(df["bp_systolic"].median(), 2),
        "diastolic_median": round(df["bp_diastolic"].median(), 2),
    }


def calc_std_sugar(df):
    return {
        "mean": round(df["sugar_fasting"].mean(), 2),
        "std": round(df["sugar_fasting"].std(), 2),
    }


def score_patient_risk(patient: HasVitals) -> str:
    """Delegates to the threshold scorer; results unchanged."""
    return _DEFAULT_SCORER.score(patient)
