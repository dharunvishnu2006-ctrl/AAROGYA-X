from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr import models
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m2_his.hospitals import HOSPITAL_NETWORK, Hospital
from aarogya.m2_his.occupancy import hospital_occupancy
from aarogya.platform import paths


def test_occupancy_rate():
    h = Hospital("H9", "Test Hospital", "Chennai", 200)
    assert h.occupancy_rate(50) == 25.0
    assert h.occupancy_rate(1) == 0.5


def test_zero_beds_returns_zero():
    assert Hospital("H9", "Empty", "Delhi", 0).occupancy_rate(10) == 0.0


def test_network_uses_single_class():
    assert all(isinstance(h, Hospital) for h in HOSPITAL_NETWORK)
    assert [h.hospital_id for h in HOSPITAL_NETWORK] == [
        "H001",
        "H002",
        "H003",
    ]


def test_network_names_are_synthetic():
    assert all(h.name.startswith("AAROGYA ") for h in HOSPITAL_NETWORK)


def test_seed_never_over_capacity(tmp_path):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(
        db_path, paths.SEED_CSV, paths.HOSPITALS_CSV, paths.STAYS_CSV
    )
    conn = cs.get_connection(str(db_path))
    try:
        rows = hospital_occupancy(conn)
    finally:
        conn.close()
    assert len(rows) == len(HOSPITAL_NETWORK)
    assert not [r["hospital_id"] for r in rows if r["over_capacity"]]


def test_models_has_no_hospital_copy():
    assert not hasattr(models, "Hospital")
