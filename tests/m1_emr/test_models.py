from aarogya.m1_emr.models import Patient


def test_patient_creation():
    p = Patient("P001", "Arjun", 28, "Male", 22.5, 118, 75, 95, "Chennai")
    assert p.patient_id == "P001"
    assert p.name == "Arjun"


def test_bmi_category():
    p = Patient("P002", "Priya", 35, "Female", 31.0, 125, 80, 100, "Mumbai")
    assert p.get_bmi_category() == "Obese"
