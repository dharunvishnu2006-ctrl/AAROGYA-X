import io

from aarogya.m14_audit.logging_setup import log_event
from aarogya.m2_his import loader, stays
from aarogya.m2_his.hospitals import count_hospitals, get_hospitals

HOSPITALS_TEXT = (
    "hospital_id,name,city,total_beds\n"
    "H010,Alpha,Chennai,10\n"
    "H011,Beta,Delhi,abc\n"
    "H012,Gamma,Pune,-1\n"
    "H010,Alpha Again,Chennai,5\n"
    ",NoId,Pune,5\n"
)
STAY_HEADER = "patient_id,hospital_id,ward,bed,admitted_at,discharged_at\n"


def _csv(text):
    return loader.extract_csv(io.StringIO(text))


def test_load_hospitals_counts_and_quarantine(db):
    result = loader.load_hospitals(db, _csv(HOSPITALS_TEXT))
    assert (result.rows_read, result.accepted, result.rejected) == (5, 1, 4)
    reasons = {q["row"]: q["reason"] for q in result.quarantine}
    assert "whole number" in reasons[2]
    assert "negative" in reasons[3]
    assert reasons[4] == loader.DUPLICATE_HOSPITAL_REASON
    assert "hospital_id cannot be empty" in reasons[5]
    assert [h.name for h in get_hospitals(db)] == ["Alpha"]


def test_missing_hospital_column_quarantines_all(db):
    result = loader.load_hospitals(db, _csv("hospital_id,name\nH1,A\n"))
    assert result.accepted == 0
    assert "Missing columns: city, total_beds" in (
        result.quarantine[0]["reason"]
    )
    assert count_hospitals(db) == 0


def test_load_stays_applies_every_rule(his_db, at):
    text = STAY_HEADER + "\n".join(
        [
            f"P001,H001,General,B01,{at(1)},{at(3)}",
            f"P002,H001,General,B01,{at(4)},",
            f"P002,H002,ICU,B01,{at(5)},",
            f"P003,H001,General,B01,{at(5)},",
            f"P004,H001,General,B02,{at(6)},{at(5)}",
            f"P999,H001,General,B03,{at(6)},",
            "P003,H001,General,B04,2026-09-06 08:00,",
            f"P003,H001,,B05,{at(6)},",
        ]
    )
    result = loader.load_stays(his_db, _csv(text))
    assert (result.rows_read, result.accepted) == (8, 2)
    reasons = [q["reason"] for q in result.quarantine]
    assert "already has an open stay" in reasons[0]
    assert "Bed already holds" in reasons[1]
    assert "after admission" in reasons[2]
    assert "Patient not found" in reasons[3]
    assert "UTC offset" in reasons[4]
    assert "ward cannot be empty" in reasons[5]
    # Check refused rows left nothing open
    assert stays.get_stays(his_db, "P004") == []
    assert len(stays.get_open_stays(his_db)) == 1


def test_quarantine_rows_hold_no_patient_id(his_db, at):
    text = STAY_HEADER + f"P999,H001,General,B01,{at(1)},\n"
    result = loader.load_stays(his_db, _csv(text))
    assert set(result.quarantine[0]) == {"row", "reason"}
    assert "P999" not in result.quarantine[0]["reason"]


def test_extract_keeps_ids_as_text():
    df = _csv("hospital_id,name,city,total_beds\n007,A,B,1\n")
    assert df.loc[0, "hospital_id"] == "007"


def test_load_log_line_holds_counts_only(his_db, at, log_file, read_log):
    text = STAY_HEADER + "\n".join(
        [
            f"P001,H001,General,B01,{at(1)},",
            f"P002,H001,General,B01,{at(2)},",
        ]
    )
    result = loader.load_stays(his_db, _csv(text))
    log_event(
        "stays_loaded",
        "m2_his",
        rows_read=result.rows_read,
        accepted=result.accepted,
        rejected=result.rejected,
    )
    line = read_log(log_file)[0]
    assert line["event"] == "stays_loaded"
    assert (line["rows_read"], line["accepted"], line["rejected"]) == (
        2,
        1,
        1,
    )
    body = " ".join(str(v) for k, v in line.items() if k != "run_id")
    assert "P0" not in body and "H00" not in body and "B01" not in body


def test_empty_stays_csv_loads_nothing(his_db):
    result = loader.load_stays(his_db, _csv(STAY_HEADER))
    assert (result.rows_read, result.accepted) == (0, 0)
