import pandas as pd
from aarogya.m1_emr.models import Patient
from aarogya.m6_risk.analytics import calc_avg_bmi, score_patient_risk


def test_calc_avg_bmi(sample_csv):
    df = pd.read_csv(sample_csv)
    result = calc_avg_bmi(df)
    assert isinstance(result, dict)
    assert "mean" in result


def test_high_risk_patient():
    p = Patient("P003", "Ravi", 55, "Male", 38.0, 185, 110, 220, "Delhi")
    assert score_patient_risk(p) == "High"
