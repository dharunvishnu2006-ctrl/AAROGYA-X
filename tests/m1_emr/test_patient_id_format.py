import pytest

from aarogya.m1_emr.ingest import ingest_dataframe
from aarogya.m1_emr.models import PATIENT_ID_FORMAT_MESSAGE, Patient


def make(pid):
    return Patient(pid, "Pushti Jain", 40, "F", 24.0, 130, 85, 100, "Pune")


@pytest.mark.parametrize(
    "pid", ["7", "p007", "PX01", "P07", "", " P007", "P007\n", None]
)
def test_malformed_id_rejected_with_format(pid):
    with pytest.raises(ValueError) as err:
        make(pid)
    assert str(err.value) == PATIENT_ID_FORMAT_MESSAGE
    assert "^P[0-9]{3,}$" in str(err.value)


@pytest.mark.parametrize("pid", ["P007", "P1234"])
def test_wellformed_id_accepted(pid):
    assert make(pid).patient_id == pid


def test_upload_row_with_bad_id_quarantined(db, sample_df):
    sample_df.loc[0, "patient_id"] = "p001"
    result = ingest_dataframe(db, sample_df)
    assert result.accepted == 3
    assert result.quarantine[0]["reason"] == PATIENT_ID_FORMAT_MESSAGE
