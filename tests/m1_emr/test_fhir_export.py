"""FHIR R4B export: built only from the store, validated, no name."""

import json
from datetime import datetime
from pathlib import Path

import pytest
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient as FhirPatient

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr import fhir_export as fx
from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m1_emr.models import Patient
from aarogya.m2_his.hospitals import Hospital, insert_hospital
from aarogya.m2_his.stays import admit, discharge

MODELS = {
    "Patient": FhirPatient,
    "Observation": Observation,
    "Encounter": Encounter,
}


@pytest.fixture
def store(db, sample_df):
    ingest_dataframe(db, sample_df)
    insert_hospital(db, Hospital("H001", "Test Chennai", "Chennai", 2))
    return db


def resources(bundle, kind):
    return [
        entry["resource"]
        for entry in bundle["entry"]
        if entry["resource"]["resourceType"] == kind
    ]


def observation(bundle, suffix):
    (found,) = [
        res
        for res in resources(bundle, "Observation")
        if res["id"].endswith(f"-{suffix}")
    ]
    return found


def coding(concept):
    (code,) = concept["coding"]
    return code


def same_time(fhir_text, stored_text):
    parse = datetime.fromisoformat
    return parse(fhir_text) == parse(stored_text)


def test_bundle_shape_without_stays(store):
    bundle = fx.patient_bundle(store, "P001")
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert len(resources(bundle, "Patient")) == 1
    assert len(resources(bundle, "Observation")) == 3
    assert resources(bundle, "Encounter") == []


def test_unknown_patient_returns_none(store):
    assert fx.patient_bundle(store, "P999") is None


def test_patient_has_only_stored_fields(store):
    (patient,) = resources(fx.patient_bundle(store, "P001"), "Patient")
    assert patient == {
        "resourceType": "Patient",
        "id": "P001",
        "gender": "female",
        "address": [{"city": "Chennai"}],
    }


@pytest.mark.parametrize(
    "stored, code", [("M", "male"), ("F", "female"), ("Other", "other")]
)
def test_gender_maps_to_fhir_codes(db, stored, code):
    cs.insert_patient(
        db, Patient("P100", "X", 40, stored, 24, 120, 80, 90, "Pune")
    )
    (patient,) = resources(fx.patient_bundle(db, "P100"), "Patient")
    assert patient["gender"] == code


def test_bp_panel_with_two_components(store):
    row = cs.get_patient(store, "P002")
    bp = observation(fx.patient_bundle(store, "P002"), "bp")
    assert coding(bp["code"])["code"] == "85354-9"
    assert coding(bp["code"])["system"] == "http://loinc.org"
    assert coding(bp["category"][0])["code"] == "vital-signs"
    assert "valueQuantity" not in bp
    parts = {
        coding(part["code"])["code"]: part["valueQuantity"]
        for part in bp["component"]
    }
    assert set(parts) == {"8480-6", "8462-4"}
    assert parts["8480-6"]["value"] == row["bp_systolic"]
    assert parts["8462-4"]["value"] == row["bp_diastolic"]
    for quantity in parts.values():
        assert quantity["code"] == "mm[Hg]"
        assert quantity["system"] == "http://unitsofmeasure.org"


@pytest.mark.parametrize(
    "suffix, loinc, unit, category, field",
    [
        ("bmi", "39156-5", "kg/m2", "vital-signs", "bmi"),
        ("glucose", "1558-6", "mg/dL", "laboratory", "sugar_fasting"),
    ],
)
def test_single_value_observations(
    store, suffix, loinc, unit, category, field
):
    row = cs.get_patient(store, "P002")
    obs = observation(fx.patient_bundle(store, "P002"), suffix)
    assert coding(obs["code"])["code"] == loinc
    assert coding(obs["category"][0])["code"] == category
    assert obs["valueQuantity"]["value"] == row[field]
    assert obs["valueQuantity"]["code"] == unit
    assert obs["valueQuantity"]["system"] == "http://unitsofmeasure.org"


def test_observations_final_subject_and_stored_time(store):
    row = cs.get_patient(store, "P003")
    bundle = fx.patient_bundle(store, "P003")
    for obs in resources(bundle, "Observation"):
        assert obs["status"] == "final"
        assert obs["subject"] == {"reference": "Patient/P003"}
        assert same_time(obs["effectiveDateTime"], row["updated_at"])


def test_open_stay_is_in_progress_encounter(store):
    admit(store, "P001", "H001", "W1", "B1", "2026-09-01T08:00:00+00:00")
    (enc,) = resources(fx.patient_bundle(store, "P001"), "Encounter")
    assert enc["status"] == "in-progress"
    assert enc["class"]["code"] == "IMP"
    assert enc["subject"] == {"reference": "Patient/P001"}
    assert same_time(enc["period"]["start"], "2026-09-01T08:00:00+00:00")
    assert "end" not in enc["period"]


def test_discharged_stay_is_finished_encounter(store):
    admit(store, "P001", "H001", "W1", "B1", "2026-09-01T08:00:00+00:00")
    discharge(store, "P001", "2026-09-03T10:30:00+00:00")
    (enc,) = resources(fx.patient_bundle(store, "P001"), "Encounter")
    assert enc["status"] == "finished"
    assert same_time(enc["period"]["end"], "2026-09-03T10:30:00+00:00")


def test_one_encounter_per_stay(store):
    admit(store, "P001", "H001", "W1", "B1", "2026-09-01T08:00:00+00:00")
    discharge(store, "P001", "2026-09-02T08:00:00+00:00")
    admit(store, "P001", "H001", "W1", "B1", "2026-09-05T08:00:00+00:00")
    encounters = resources(fx.patient_bundle(store, "P001"), "Encounter")
    assert [enc["status"] for enc in encounters] == [
        "finished",
        "in-progress",
    ]
    assert len({enc["id"] for enc in encounters}) == 2


def test_every_resource_passes_validator(store):
    admit(store, "P002", "H001", "W1", "B1", "2026-09-01T08:00:00+00:00")
    bundle = fx.patient_bundle(store, "P002")
    Bundle.model_validate(bundle)
    for entry in bundle["entry"]:
        res = entry["resource"]
        MODELS[res["resourceType"]].model_validate(res)


def test_no_name_or_birth_date_anywhere(store, sample_df):
    admit(store, "P001", "H001", "W1", "B1", "2026-09-01T08:00:00+00:00")
    text = json.dumps(fx.patient_bundle(store, "P001"))
    assert '"name"' not in text
    assert "birthDate" not in text
    for name in sample_df["name"]:
        for part in name.split():
            assert part not in text


def test_module_makes_no_compliance_claim():
    source = Path(fx.__file__).read_text(encoding="utf-8").lower()
    assert "abdm" not in source
    assert "certified" not in source
