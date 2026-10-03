from dataclasses import dataclass


@dataclass(frozen=True)
class ClinicalThreshold:
    value: float
    source: str
    rationale: str


WHO_BMI = "World Health Organization (WHO) adult BMI classification"
WHO_HTN = (
    "World Health Organization (WHO) guideline for the pharmacological "
    "treatment of hypertension in adults"
)

# Kept for reference and demographic reporting; not used in
# score_patient_risk() because underweight (<18.5) reflects
# frailty/malnutrition rather than additive metabolic/cardiovascular
# triage risk.
BMI_UNDERWEIGHT = ClinicalThreshold(
    value=18.5,
    source=WHO_BMI,
    rationale="Adult BMI below 18.5 kg/m² is classified as underweight.",
)

BMI_OVERWEIGHT = ClinicalThreshold(
    value=25.0,
    source=WHO_BMI,
    rationale=(
        "Adult BMI of 25.0 kg/m² or higher is classified as overweight."
    ),
)

BMI_OBESITY = ClinicalThreshold(
    value=30.0,
    source=WHO_BMI,
    rationale="Adult BMI of 30.0 kg/m² or higher is classified as obesity.",
)

BP_SYSTOLIC_HIGH = ClinicalThreshold(
    value=140.0,
    source=WHO_HTN,
    rationale=(
        "WHO establishes systolic BP >= 140 mmHg as the diagnostic "
        "threshold for hypertension and the initiation trigger for "
        "pharmacological treatment in adults."
    ),
)

BP_DIASTOLIC_HIGH = ClinicalThreshold(
    value=90.0,
    source=WHO_HTN,
    rationale=(
        "WHO pairs diastolic BP >= 90 mmHg with systolic 140 mmHg as the "
        "complementary diagnostic threshold for hypertension."
    ),
)

FASTING_SUGAR_DIABETES = ClinicalThreshold(
    value=126.0,
    source=(
        "American Diabetes Association (ADA) Standards of Care in Diabetes"
    ),
    rationale=(
        "Fasting plasma glucose >= 126 mg/dL meets established clinical "
        "diagnostic criteria for diabetes mellitus."
    ),
)
