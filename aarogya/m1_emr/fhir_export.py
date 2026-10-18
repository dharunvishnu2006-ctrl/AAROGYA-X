"""M1 EMR: FHIR R4B export of one patient record; export only.

patient_bundle builds a Bundle (type "collection") only from what the
store holds: a Patient (no name, no birthDate), one Observation per
vital and one Encounter per stay. Every resource is built with the
fhir.resources R4B models, so a wrong structure fails here, not at
the reader. Every query reads one table.
"""

import sqlite3
from typing import Any, Dict, List, Optional

from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.encounter import Encounter
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient as FhirPatient

from aarogya.m1_emr import clinical_store as cs
from aarogya.m2_his.stays import get_stays

LOINC = "http://loinc.org"
UCUM = "http://unitsofmeasure.org"
CATEGORY_SYSTEM = (
    "http://terminology.hl7.org/CodeSystem/observation-category"
)
ACT_CODE_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ActCode"

BP_PANEL = ("85354-9", "Blood pressure panel with all children optional")
SYSTOLIC = ("8480-6", "Systolic blood pressure")
DIASTOLIC = ("8462-4", "Diastolic blood pressure")
BMI = ("39156-5", "Body mass index (BMI) [Ratio]")
GLUCOSE = ("1558-6", "Fasting glucose [Mass/volume] in Serum or Plasma")

MM_HG = "mm[Hg]"
KG_M2 = "kg/m2"
MG_DL = "mg/dL"

VITAL_SIGNS = "vital-signs"
LABORATORY = "laboratory"

# Map stored gender to FHIR codes
GENDER_CODES = {"M": "male", "F": "female", "Other": "other"}

ENCOUNTER_OPEN = "in-progress"
ENCOUNTER_CLOSED = "finished"


def _coding(system: str, code: str, display: str) -> Dict[str, Any]:
    return {"system": system, "code": code, "display": display}


def _concept(loinc: tuple) -> Dict[str, Any]:
    return {"coding": [_coding(LOINC, *loinc)], "text": loinc[1]}


def _quantity(value: float, unit: str) -> Dict[str, Any]:
    return {"value": value, "unit": unit, "system": UCUM, "code": unit}


def _category(code: str) -> List[Dict[str, Any]]:
    display = "Vital Signs" if code == VITAL_SIGNS else "Laboratory"
    return [{"coding": [_coding(CATEGORY_SYSTEM, code, display)]}]


def _patient(row: Dict[str, Any]) -> FhirPatient:
    return FhirPatient.model_validate(
        {
            "resourceType": "Patient",
            "id": row["patient_id"],
            "gender": GENDER_CODES[row["gender"]],
            "address": [{"city": row["city"]}],
        }
    )


def _observation_base(
    row: Dict[str, Any], suffix: str, category: str, loinc: tuple
) -> Dict[str, Any]:
    return {
        "resourceType": "Observation",
        "id": f"{row['patient_id']}-{suffix}",
        "status": "final",
        "category": _category(category),
        "code": _concept(loinc),
        "subject": {"reference": f"Patient/{row['patient_id']}"},
        "effectiveDateTime": row["updated_at"],
    }


def _bp_observation(row: Dict[str, Any]) -> Observation:
    data = _observation_base(row, "bp", VITAL_SIGNS, BP_PANEL)
    data["component"] = [
        {
            "code": _concept(SYSTOLIC),
            "valueQuantity": _quantity(row["bp_systolic"], MM_HG),
        },
        {
            "code": _concept(DIASTOLIC),
            "valueQuantity": _quantity(row["bp_diastolic"], MM_HG),
        },
    ]
    return Observation.model_validate(data)


def _quantity_observation(
    row: Dict[str, Any],
    suffix: str,
    category: str,
    loinc: tuple,
    field: str,
    unit: str,
) -> Observation:
    data = _observation_base(row, suffix, category, loinc)
    data["valueQuantity"] = _quantity(row[field], unit)
    return Observation.model_validate(data)


def _encounter(stay: Dict[str, Any]) -> Encounter:
    period = {"start": stay["admitted_at"]}
    if stay["discharged_at"] is not None:
        period["end"] = stay["discharged_at"]
    status = ENCOUNTER_OPEN if "end" not in period else ENCOUNTER_CLOSED
    return Encounter.model_validate(
        {
            "resourceType": "Encounter",
            "id": f"stay-{stay['stay_id']}",
            "status": status,
            "class": _coding(ACT_CODE_SYSTEM, "IMP", "inpatient encounter"),
            "subject": {"reference": f"Patient/{stay['patient_id']}"},
            "period": period,
        }
    )


def patient_bundle(
    conn: sqlite3.Connection, patient_id: str
) -> Optional[Dict[str, Any]]:
    """Returns one patient's FHIR Bundle as JSON data; None if unknown."""
    row = cs.get_patient(conn, patient_id)
    if row is None:
        return None
    resources: List[Any] = [
        _patient(row),
        _bp_observation(row),
        _quantity_observation(row, "bmi", VITAL_SIGNS, BMI, "bmi", KG_M2),
        _quantity_observation(
            row, "glucose", LABORATORY, GLUCOSE, "sugar_fasting", MG_DL
        ),
    ]
    resources += [_encounter(stay) for stay in get_stays(conn, patient_id)]
    bundle = Bundle.model_validate(
        {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [{"resource": res} for res in resources],
        }
    )
    return bundle.model_dump(mode="json", exclude_none=True)
