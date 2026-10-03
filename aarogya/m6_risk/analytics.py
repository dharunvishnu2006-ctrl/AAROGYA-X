from aarogya.m6_risk.clinical_config import (
    BMI_OBESITY,
    BP_DIASTOLIC_HIGH,
    BP_SYSTOLIC_HIGH,
    FASTING_SUGAR_DIABETES,
)


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


def score_patient_risk(patient) -> str:
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
