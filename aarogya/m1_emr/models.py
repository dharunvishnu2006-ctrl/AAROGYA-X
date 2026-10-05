import re
from typing import Any, Tuple

from aarogya.m6_risk.clinical_config import (
    AGE_RANGE,
    BMI_OBESITY,
    BMI_OVERWEIGHT,
    BMI_RANGE,
    BMI_UNDERWEIGHT,
    BP_DIASTOLIC_HIGH,
    BP_DIASTOLIC_RANGE,
    BP_SYSTOLIC_HIGH,
    BP_SYSTOLIC_RANGE,
    FASTING_SUGAR_DIABETES,
    SUGAR_FASTING_RANGE,
)
from aarogya.m6_risk.scoring import RISK_RANK, ThresholdRiskScorer

PATIENT_ID_PATTERN = re.compile(r"P[0-9]{3,}")
PATIENT_ID_FORMAT_MESSAGE = (
    "Invalid patient_id: expected 'P' followed by at least 3 digits "
    "(format ^P[0-9]{3,}$, e.g. P007)."
)

_TRIAGE_SCORER = ThresholdRiskScorer()


class Person:
    def __init__(self, person_id: str, name: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Name cannot be empty.")
        self._person_id = person_id
        self.name = name

    @property
    def person_id(self) -> str:
        return self._person_id


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"All vitals must be numeric values. Error: {e}")


def _check_age(value: Any) -> int:
    try:
        age = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Age must be a valid number, got {value!r}.")
    if not AGE_RANGE.contains(age):
        raise ValueError(
            f"Age {age} is outside the plausible human range "
            f"({AGE_RANGE.low:g}-{AGE_RANGE.high:g})."
        )
    return age


def _check_bmi(bmi: float) -> float:
    if not BMI_RANGE.contains(bmi):
        raise ValueError(
            f"BMI {bmi} is physiologically implausible "
            f"(expected {BMI_RANGE.low:.1f}-{BMI_RANGE.high:.1f})."
        )
    return bmi


def _check_systolic(sbp: float) -> float:
    if not BP_SYSTOLIC_RANGE.contains(sbp):
        raise ValueError(
            f"Systolic BP {sbp} is outside clinical measurement range "
            f"({BP_SYSTOLIC_RANGE.low:g}-{BP_SYSTOLIC_RANGE.high:g})."
        )
    return sbp


def _check_diastolic(dbp: float) -> float:
    if not BP_DIASTOLIC_RANGE.contains(dbp):
        raise ValueError(
            f"Diastolic BP {dbp} is outside clinical measurement range "
            f"({BP_DIASTOLIC_RANGE.low:g}-{BP_DIASTOLIC_RANGE.high:g})."
        )
    return dbp


def _check_bp_order(sbp: float, dbp: float) -> None:
    if sbp <= dbp:
        raise ValueError(
            f"Systolic BP ({sbp}) must be greater than "
            f"Diastolic BP ({dbp})."
        )


def _check_sugar(sugar: float) -> float:
    if not SUGAR_FASTING_RANGE.contains(sugar):
        raise ValueError(
            f"Fasting blood sugar {sugar} is outside viable clinical "
            f"limits ({SUGAR_FASTING_RANGE.low:g}-"
            f"{SUGAR_FASTING_RANGE.high:g})."
        )
    return sugar


def _normalise_gender(gender: Any) -> str:
    clean_gender = str(gender).strip().upper() if gender else ""
    if clean_gender in {"M", "MALE"}:
        return "M"
    if clean_gender in {"F", "FEMALE"}:
        return "F"
    if clean_gender in {"OTHER", "O"}:
        return "Other"
    raise ValueError(
        f"Invalid gender '{gender}'. Allowed: 'M', 'F', 'Other'."
    )


def _check_patient_id(patient_id: Any) -> str:
    if not isinstance(patient_id, str) or not PATIENT_ID_PATTERN.fullmatch(
        patient_id
    ):
        raise ValueError(PATIENT_ID_FORMAT_MESSAGE)
    return patient_id


class Patient(Person):
    """One patient record; identity is the patient_id alone."""

    def __init__(
        self,
        patient_id,
        name,
        age,
        gender,
        bmi,
        bp_systolic,
        bp_diastolic,
        sugar_fasting,
        city,
    ):
        super().__init__(_check_patient_id(patient_id), name)
        self._age = _check_age(age)
        self.gender = _normalise_gender(gender)
        # Coerce every vital before range checks
        bmi_f = _to_float(bmi)
        sbp_f = _to_float(bp_systolic)
        dbp_f = _to_float(bp_diastolic)
        sugar_f = _to_float(sugar_fasting)
        self._bmi = _check_bmi(bmi_f)
        self._bp_systolic = _check_systolic(sbp_f)
        self._bp_diastolic = _check_diastolic(dbp_f)
        _check_bp_order(self._bp_systolic, self._bp_diastolic)
        self._sugar_fasting = _check_sugar(sugar_f)
        self.city = city

    @property
    def patient_id(self) -> str:
        return self.person_id

    @property
    def age(self) -> int:
        return self._age

    @age.setter
    def age(self, value: Any) -> None:
        self._age = _check_age(value)

    @property
    def bmi(self) -> float:
        return self._bmi

    @bmi.setter
    def bmi(self, value: Any) -> None:
        self._bmi = _check_bmi(_to_float(value))

    @property
    def bp_systolic(self) -> float:
        return self._bp_systolic

    @bp_systolic.setter
    def bp_systolic(self, value: Any) -> None:
        sbp = _check_systolic(_to_float(value))
        _check_bp_order(sbp, self._bp_diastolic)
        self._bp_systolic = sbp

    @property
    def bp_diastolic(self) -> float:
        return self._bp_diastolic

    @bp_diastolic.setter
    def bp_diastolic(self, value: Any) -> None:
        dbp = _check_diastolic(_to_float(value))
        _check_bp_order(self._bp_systolic, dbp)
        self._bp_diastolic = dbp

    @property
    def sugar_fasting(self) -> float:
        return self._sugar_fasting

    @sugar_fasting.setter
    def sugar_fasting(self, value: Any) -> None:
        self._sugar_fasting = _check_sugar(_to_float(value))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Patient):
            return NotImplemented
        return self.patient_id == other.patient_id

    def __hash__(self) -> int:
        return hash(self.patient_id)

    def _triage_key(self) -> Tuple[int, int, str]:
        rank = RISK_RANK[_TRIAGE_SCORER.score(self)]
        return (rank, int(self.patient_id[1:]), self.patient_id)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Patient):
            return NotImplemented
        return self._triage_key() < other._triage_key()

    def __str__(self) -> str:
        parts = self.name.split()
        if len(parts) > 1:
            short = f"{parts[0]} {parts[-1][0].upper()}."
        else:
            short = parts[0]
        return f"{self.patient_id} · {short}"

    def __repr__(self) -> str:
        return f"Patient({self})"

    def get_bmi_category(self):
        if self.bmi < BMI_UNDERWEIGHT.value:
            return "Underweight"
        elif self.bmi < BMI_OVERWEIGHT.value:
            return "Normal"
        elif self.bmi < BMI_OBESITY.value:
            return "Overweight"
        else:
            return "Obese"

    def is_hypertensive(self):
        return (
            self.bp_systolic >= BP_SYSTOLIC_HIGH.value
            or self.bp_diastolic >= BP_DIASTOLIC_HIGH.value
        )

    def is_diabetic(self):
        return self.sugar_fasting >= FASTING_SUGAR_DIABETES.value
