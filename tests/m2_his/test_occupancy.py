from aarogya.m1_emr import clinical_store as cs
from aarogya.m2_his.occupancy import hospital_occupancy
from aarogya.m2_his.stays import admit, discharge


def _by_id(conn):
    return {row["hospital_id"]: row for row in hospital_occupancy(conn)}


def test_chennai_patients_without_stays_is_zero(his_db, at):
    # Admit Chennai resident to Delhi
    assert cs.get_patient(his_db, "P001")["city"] == "Chennai"
    admit(his_db, "P001", "H002", "General", "B01", at(1))
    chennai = _by_id(his_db)["H001"]
    assert chennai["open_stays"] == 0
    assert chennai["occupancy_pct"] == 0.0
    assert chennai["over_capacity"] is False


def test_open_stays_over_total_beds(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    assert _by_id(his_db)["H001"]["occupancy_pct"] == 25.0


def test_discharged_stays_do_not_count(his_db, at):
    admit(his_db, "P001", "H001", "General", "B01", at(1))
    admit(his_db, "P002", "H001", "General", "B02", at(1))
    discharge(his_db, "P002", at(2))
    row = _by_id(his_db)["H001"]
    assert row["open_stays"] == 1
    assert row["occupancy_pct"] == 25.0


def test_above_100_shown_and_flagged(his_db, at):
    for bed, pid in enumerate(["P001", "P002", "P003"], start=1):
        admit(his_db, pid, "H002", "General", f"B{bed:02d}", at(1))
    delhi = _by_id(his_db)["H002"]
    assert delhi["open_stays"] == 3
    assert delhi["occupancy_pct"] == 150.0
    assert delhi["over_capacity"] is True


def test_exactly_full_is_not_over_capacity(his_db, at):
    admit(his_db, "P001", "H002", "General", "B01", at(1))
    admit(his_db, "P002", "H002", "General", "B02", at(1))
    delhi = _by_id(his_db)["H002"]
    assert delhi["occupancy_pct"] == 100.0
    assert delhi["over_capacity"] is False


def test_zero_beds_with_stays_has_no_rate(his_db, at):
    admit(his_db, "P001", "H003", "General", "B01", at(1))
    pune = _by_id(his_db)["H003"]
    assert pune["open_stays"] == 1
    assert pune["occupancy_pct"] is None
    assert pune["over_capacity"] is True


def test_zero_beds_without_stays_has_no_rate(his_db):
    pune = _by_id(his_db)["H003"]
    assert pune["occupancy_pct"] is None
    assert pune["over_capacity"] is False


def test_every_hospital_listed_in_id_order(his_db):
    ids = [row["hospital_id"] for row in hospital_occupancy(his_db)]
    assert ids == ["H001", "H002", "H003"]


def test_city_change_does_not_move_occupancy(his_db, at):
    admit(his_db, "P002", "H001", "General", "B01", at(1))
    before = hospital_occupancy(his_db)
    cs.correct_patient_vital(his_db, "P002", "city", "Chennai", "Moved")
    cs.correct_patient_vital(his_db, "P003", "city", "Chennai", "Moved")
    assert hospital_occupancy(his_db) == before


def test_empty_store_gives_empty_list(db):
    assert hospital_occupancy(db) == []
