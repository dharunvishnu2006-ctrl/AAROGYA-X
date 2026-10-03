from aarogya.m6_risk.clinical_config import (
    BMI_UNDERWEIGHT,
    BMI_OVERWEIGHT,
    BMI_OBESITY,
    BP_SYSTOLIC_HIGH,
    BP_DIASTOLIC_HIGH,
    FASTING_SUGAR_DIABETES,
)


class Person:
    def __init__(self, name: str, age: int, gender: str):
        self.name = name
        self.age = age
        self.gender = gender
        self._validate_person()

    def _validate_person(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Name cannot be empty.")

        try:
            self.age = int(self.age)
        except (ValueError, TypeError):
            raise ValueError(
                f"Age must be a valid number, got {self.age!r}."
            )

        if not (0 <= self.age <= 125):
            raise ValueError(
                f"Age {self.age} is outside the plausible human range "
                "(0-125)."
            )

        clean_gender = (
            str(self.gender).strip().upper() if self.gender else ""
        )
        if clean_gender in {"M", "MALE"}:
            self.gender = "M"
        elif clean_gender in {"F", "FEMALE"}:
            self.gender = "F"
        elif clean_gender in {"OTHER", "O"}:
            self.gender = "Other"
        else:
            raise ValueError(
                f"Invalid gender '{self.gender}'. "
                "Allowed: 'M', 'F', 'Other'."
            )


class Patient(Person):
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
        super().__init__(name, age, gender)
        self.patient_id = patient_id
        self.bmi = bmi
        self.bp_systolic = bp_systolic
        self.bp_diastolic = bp_diastolic
        self.sugar_fasting = sugar_fasting
        self.city = city
        self._validate_vitals()

    def _validate_vitals(self):
        try:
            self.bmi = float(self.bmi)
            self.bp_systolic = float(self.bp_systolic)
            self.bp_diastolic = float(self.bp_diastolic)
            self.sugar_fasting = float(self.sugar_fasting)
        except (ValueError, TypeError) as e:
            raise ValueError(
                f"All vitals must be numeric values. Error: {e}"
            )

        if not (10.0 <= self.bmi <= 90.0):
            raise ValueError(
                f"BMI {self.bmi} is physiologically implausible "
                "(expected 10.0-90.0)."
            )
        if not (50.0 <= self.bp_systolic <= 300.0):
            raise ValueError(
                f"Systolic BP {self.bp_systolic} is outside clinical "
                "measurement range (50-300)."
            )
        if not (30.0 <= self.bp_diastolic <= 200.0):
            raise ValueError(
                f"Diastolic BP {self.bp_diastolic} is outside clinical "
                "measurement range (30-200)."
            )
        if self.bp_systolic <= self.bp_diastolic:
            raise ValueError(
                f"Systolic BP ({self.bp_systolic}) must be greater than "
                f"Diastolic BP ({self.bp_diastolic})."
            )
        if not (30.0 <= self.sugar_fasting <= 700.0):
            raise ValueError(
                f"Fasting blood sugar {self.sugar_fasting} is outside "
                "viable clinical limits (30-700)."
            )

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


class Doctor(Person):
    def __init__(self, doctor_id, name, age, gender, specialty, hospital):
        super().__init__(name, age, gender)
        self.doctor_id = doctor_id
        self.specialty = specialty
        self.hospital = hospital
        self.assigned_patients = []

    def add_patient(self, patient):
        self.assigned_patients.append(patient)

    def get_assigned_patients(self):
        return self.assigned_patients
