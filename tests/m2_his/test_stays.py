import pytest

from aarogya.m2_his import stays
from aarogya.m2_his.stays import StayError, admit, discharge


def test_admit_opens_one_stay(his_db, at):
    stay_id = admit(his_db, "P001", "H001", "General", "B01", at(1))
    open_stays = stays.get_open_stays(his_db)
    assert [s["stay_id"] for s in open_stays] == [stay_id]
    assert open_stays[0]["admitted_at"] == at(1)
    assert open_stays[0]["discharged_at"] is None


def test_same_patient_twice_refused(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    with pytest.raises(StayError, match="already has an open stay"):
        admit(his_db, "P001", "H002", "ICU", "B01", at(2))
    assert stays.count_stays(his_db) == 1


def test_occupied_bed_refused(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    with pytest.raises(StayError, match="Bed already holds"):
        admit(his_db, "P002", "H001", "General", "B01", at(2))


def test_same_bed_label_other_ward_allowed(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    admit(his_db, "P002", "H001", "ICU", "B01", at(1))
    assert stays.count_stays(his_db) == 2


def test_discharge_never_admitted_refused(his_db, at):
    with pytest.raises(StayError, match="never admitted"):
        discharge(his_db, "P001", at(2))


def test_discharge_before_admission_refused(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(5))
    with pytest.raises(StayError, match="after admission"):
        discharge(his_db, "P001", at(4))
    assert stays.get_open_stays(his_db)[0]["discharged_at"] is None


def test_discharge_at_admission_time_refused(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(5))
    with pytest.raises(StayError, match="after admission"):
        discharge(his_db, "P001", at(5))


def test_discharge_compares_instants_not_text(his_db):
    admit(
        his_db,
        "P001",
        "H001",
        "General",
        "B01",
        "2026-09-05T10:00:00+00:00",
    )
    # Compare instants: 15:00 IST = 09:30Z
    with pytest.raises(StayError, match="after admission"):
        discharge(his_db, "P001", "2026-09-05T15:00:00+05:30")


def test_discharge_frees_bed_and_patient(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    discharge(his_db, "P001", at(3))
    admit(his_db, "P002", "H001", "General", "B01", at(4))
    admit(his_db, "P001", "H002", "ICU", "B01", at(6))
    assert len(stays.get_open_stays(his_db)) == 2
    assert len(stays.get_stays(his_db, "P001")) == 2


def test_second_discharge_refused_value_kept(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    discharge(his_db, "P001", at(3))
    with pytest.raises(StayError, match="already discharged"):
        discharge(his_db, "P001", at(9))
    assert stays.get_stays(his_db, "P001")[0]["discharged_at"] == at(3)


def test_unknown_patient_refused(his_db, at):
    with pytest.raises(StayError, match="Patient not found"):
        admit(his_db, "P999", "H001", "General", "B01", at(1))


def test_unknown_hospital_refused(his_db, at):
    with pytest.raises(StayError, match="Hospital not found"):
        admit(his_db, "P001", "H999", "General", "B01", at(1))


@pytest.mark.parametrize("when", ["2026-09-01T08:00:00", "yesterday", ""])
def test_time_without_offset_refused(his_db, when):
    with pytest.raises(StayError):
        admit(his_db, "P001", "H001", "General", "B01", when)


@pytest.mark.parametrize("ward,bed", [("", "B01"), ("ICU", "  ")])
def test_empty_ward_or_bed_refused(his_db, at, ward, bed):
    with pytest.raises(StayError, match="cannot be empty"):
        admit(his_db, "P001", "H001", ward, bed, at(1))


def test_stored_time_is_utc(his_db):
    admit(
        his_db,
        "P001",
        "H001",
        "General",
        "B01",
        "2026-09-05T13:30:00+05:30",
    )
    stored = stays.get_open_stays(his_db)[0]["admitted_at"]
    assert stored == "2026-09-05T08:00:00+00:00"


def test_stay_error_is_value_error():
    assert issubclass(StayError, ValueError)


def test_error_messages_hold_no_patient_id(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    with pytest.raises(StayError) as info:
        admit(his_db, "P001", "H001", "General", "B02", at(2))
    assert "P001" not in str(info.value)
