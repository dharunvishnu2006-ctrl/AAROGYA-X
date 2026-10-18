"""Flask test client against a temp store; no network needed."""

import json
import os

import pytest
from fhir.resources.R4B.bundle import Bundle

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE
from aarogya.m2_his.hospitals import Hospital, insert_hospital
from aarogya.m2_his.stays import admit
from aarogya.platform import api


@pytest.fixture
def store(db_file, sample_df):
    conn = cs.get_connection(str(db_file))
    ingest_dataframe(conn, sample_df)
    insert_hospital(conn, Hospital("H001", "Test Chennai", "Chennai", 2))
    insert_hospital(conn, Hospital("H002", "Test Delhi", "Delhi", 1))
    admit(conn, "P002", "H002", "ICU", "B01", "2026-09-01T08:00:00+00:00")
    admit(conn, "P003", "H002", "ICU", "B02", "2026-09-01T09:00:00+00:00")
    conn.close()
    return db_file


@pytest.fixture
def client(store):
    return api.create_app(store).test_client()


def test_health_reflects_real_store(client, store):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "healthy"
    assert body["store_reachable"] is True
    assert body["patient_count"] == 4


def test_health_count_follows_inserts(client, store, make_patient):
    conn = cs.get_connection(str(store))
    cs.insert_patient(conn, make_patient("P050"))
    conn.close()
    assert client.get("/health").get_json()["patient_count"] == 5


def test_health_unhealthy_when_store_gone(client, store, tmp_path):
    os.rename(store, tmp_path / "moved.db")
    response = client.get("/health")
    assert response.status_code == 503
    body = response.get_json()
    assert body["status"] == "unhealthy"
    assert body["store_reachable"] is False


def test_cohort_stats(client):
    response = client.get("/cohort/stats")
    assert response.status_code == 200
    body = response.get_json()
    assert body["cohort_size"] == 4
    assert set(body["vitals"]) == {
        "bmi",
        "bp_systolic",
        "bp_diastolic",
        "sugar_fasting",
    }
    assert body["vitals"]["bmi"]["count"] == 4


def test_patient_found_without_name(client, sample_df):
    response = client.get("/patients/P001")
    assert response.status_code == 200
    body = response.get_json()
    assert set(body) == {"patient_id", "age_band", "city", "vitals", "risk"}
    assert body["patient_id"] == "P001"
    text = response.get_data(as_text=True)
    assert "name" not in body
    for name in sample_df["name"]:
        for part in name.split():
            assert part not in text


def test_bad_patient_id_is_400_with_format_message(client):
    response = client.get("/patients/PX01")
    assert response.status_code == 400
    assert response.get_json() == {"error": PATIENT_ID_FORMAT_MESSAGE}


def test_unknown_patient_is_404(client):
    response = client.get("/patients/P999")
    assert response.status_code == 404
    assert response.get_json() == {"error": api.NOT_FOUND_MESSAGE}


def test_occupancy_per_hospital(client):
    response = client.get("/hospitals/occupancy")
    assert response.status_code == 200
    rows = {row["hospital_id"]: row for row in response.get_json()}
    # Expect Chennai 0%: no open stays
    assert rows["H001"]["open_stays"] == 0
    assert rows["H001"]["occupancy_pct"] == 0.0
    assert rows["H002"]["occupancy_pct"] == 200.0
    assert rows["H002"]["over_capacity"] is True


def test_patient_fhir_bundle(client, sample_df):
    response = client.get("/patients/P002/fhir")
    assert response.status_code == 200
    assert response.mimetype == api.FHIR_MIMETYPE
    bundle = json.loads(response.get_data(as_text=True))
    Bundle.model_validate(bundle)
    kinds = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert kinds.count("Patient") == 1
    assert kinds.count("Observation") == 3
    assert kinds.count("Encounter") == 1
    for entry in bundle["entry"]:
        res = entry["resource"]
        if res["resourceType"] != "Patient":
            assert res["subject"] == {"reference": "Patient/P002"}
    text = response.get_data(as_text=True)
    assert '"name"' not in text
    for name in sample_df["name"]:
        for part in name.split():
            assert part not in text


def test_patient_fhir_bad_id_is_400(client):
    response = client.get("/patients/PX01/fhir")
    assert response.status_code == 400
    assert response.get_json() == {"error": PATIENT_ID_FORMAT_MESSAGE}


def test_patient_fhir_unknown_is_404(client):
    response = client.get("/patients/P999/fhir")
    assert response.status_code == 404
    assert response.get_json() == {"error": api.NOT_FOUND_MESSAGE}


@pytest.mark.parametrize(
    "path",
    [
        "/cohort/stats",
        "/patients/P001",
        "/patients/P001/fhir",
        "/hospitals/occupancy",
    ],
)
def test_missing_store_is_503_not_500(store, tmp_path, path):
    client = api.create_app(tmp_path / "nowhere.db").test_client()
    response = client.get(path)
    assert response.status_code == 503
    assert response.get_json() == {"error": api.STORE_ERROR_MESSAGE}
    assert not (tmp_path / "nowhere.db").exists()


def test_store_without_tables_is_503(tmp_path):
    empty = tmp_path / "empty.db"
    cs.get_connection(str(empty)).close()
    client = api.create_app(empty).test_client()
    assert client.get("/hospitals/occupancy").status_code == 503


def test_deep_error_logs_class_name_only(
    client, monkeypatch, log_file, read_log
):
    def broken(conn, patient_id):
        raise ValueError(f"bad row for {patient_id}")

    monkeypatch.setattr(api.read_model, "patient_view", broken)
    response = client.get("/patients/P001")
    assert response.status_code == 503
    line = read_log(log_file)[0]
    assert line["event"] == "error"
    assert line["error_type"] == "ValueError"
    assert "P001" not in str(line)


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_api_is_read_only(client, method):
    response = getattr(client, method)("/patients/P001")
    assert response.status_code == 405


def test_unknown_route_is_json_404(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_binds_localhost_only():
    assert api.HOST == "127.0.0.1"
