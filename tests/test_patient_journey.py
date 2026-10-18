"""One synthetic patient through the whole v1.1 hospital, in order."""

import json

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe, read_patient_csv
from aarogya.m1_emr.models import Patient
from aarogya.m14_audit.logging_setup import log_event
from aarogya.m2_his.hospitals import Hospital, insert_hospital
from aarogya.m2_his.occupancy import hospital_occupancy
from aarogya.m2_his.stays import admit, discharge
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.m6_risk.scoring import RISK_RANK
from aarogya.platform import api

PID = "P900"
NAME = "Journeya Syntheticson"
CSV_TEXT = (
    "patient_id,name,age,gender,bmi,bp_systolic,bp_diastolic,"
    "sugar_fasting,city\n"
    f"{PID},{NAME},52,Female,29.4,146,92,131,Chennai\n"
)


def open_stays(conn, hospital_id):
    (row,) = [
        row
        for row in hospital_occupancy(conn)
        if row["hospital_id"] == hospital_id
    ]
    return row["open_stays"]


def encounters(client):
    response = client.get(f"/patients/{PID}/fhir")
    assert response.status_code == 200
    bundle = json.loads(response.get_data(as_text=True))
    return bundle, [
        e["resource"]
        for e in bundle["entry"]
        if e["resource"]["resourceType"] == "Encounter"
    ]


def test_one_patient_journey(tmp_path, db_file, log_file):
    # Upload one row like app.py
    csv_path = tmp_path / "upload.csv"
    csv_path.write_text(CSV_TEXT, encoding="utf-8")
    conn = cs.get_connection(str(db_file))
    result = ingest_dataframe(conn, read_patient_csv(csv_path))
    cs.record_ingest(
        conn, result.rows_read, result.accepted, result.rejected
    )
    log_event(
        "upload",
        "m1_emr",
        rows_read=result.rows_read,
        accepted=result.accepted,
        rejected=result.rejected,
    )
    assert (result.accepted, result.rejected) == (1, 0)

    # Check stored row revalidates, gets band
    row = cs.get_patient(conn, PID)
    row.pop("updated_at")
    patient = Patient(**row)
    assert score_patient_risk(patient) in RISK_RANK

    # Admit raises occupancy by one bed
    insert_hospital(conn, Hospital("H900", "Journey Test", "Chennai", 10))
    before = open_stays(conn, "H900")
    admit(conn, PID, "H900", "W1", "B1", "2026-09-01T08:00:00+00:00")
    assert open_stays(conn, "H900") == before + 1

    # Read patient through the API
    client = api.create_app(db_file).test_client()
    response = client.get(f"/patients/{PID}")
    assert response.status_code == 200
    assert response.get_json()["patient_id"] == PID
    assert "name" not in response.get_json()
    assert NAME.split()[0] not in response.get_data(as_text=True)

    # Expect Patient, Observations, open Encounter
    bundle, open_encs = encounters(client)
    kinds = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert kinds.count("Patient") == 1
    assert kinds.count("Observation") == 3
    assert [enc["status"] for enc in open_encs] == ["in-progress"]

    # Discharge restores occupancy, finishes Encounter
    discharge(conn, PID, "2026-09-04T11:00:00+00:00")
    assert open_stays(conn, "H900") == before
    _, closed_encs = encounters(client)
    assert [enc["status"] for enc in closed_encs] == ["finished"]
    conn.close()

    # Check log has lines, no patient_id
    log_text = log_file.read_text(encoding="utf-8")
    assert log_text.strip()
    assert PID not in log_text
