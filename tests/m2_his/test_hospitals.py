from aarogya.m1_emr import models
from aarogya.m2_his.hospitals import HOSPITAL_NETWORK, Hospital


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


def test_models_has_no_hospital_copy():
    assert not hasattr(models, "Hospital")
