import codecs
from datetime import date

import pytest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import (
    REQUIRED_COLUMNS,
    ingest_dataframe,
    parse_upload_date,
    read_patient_csv,
)


def test_valid_rows_all_accepted(db, sample_df):
    result = ingest_dataframe(db, sample_df)
    assert result.rows_read == 4
    assert result.accepted == 4
    assert result.skipped == 0
    assert result.rejected == 0
    assert result.quarantine == []
    assert len(cs.get_all_patients(db)) == 4


def test_invalid_rows_quarantined(db, sample_df):
    bad = sample_df.astype({"age": object})
    # Break rows 2 and 4
    bad.loc[1, "bmi"] = 5.0
    bad.loc[3, "age"] = "abc"
    result = ingest_dataframe(db, bad)
    assert result.accepted == 2
    assert result.rejected == 2
    assert [q["row"] for q in result.quarantine] == [2, 4]
    assert [q["id"] for q in result.quarantine] == ["P002", "P004"]
    assert "BMI" in result.quarantine[0]["reason"]


def test_missing_column_quarantines_every_row(db, sample_df):
    result = ingest_dataframe(db, sample_df.drop(columns=["city"]))
    assert result.accepted == 0
    assert len(result.quarantine) == 4


def test_duplicates_skipped_and_counted_rejected(db, sample_df):
    ingest_dataframe(db, sample_df)
    result = ingest_dataframe(db, sample_df.iloc[:2])
    assert result.accepted == 0
    assert result.skipped == 2
    assert result.rejected == 2
    assert result.quarantine == []


def test_duplicates_quarantined_when_flag_set(db, sample_df):
    ingest_dataframe(db, sample_df)
    result = ingest_dataframe(
        db, sample_df.iloc[:2], quarantine_duplicates=True
    )
    assert result.accepted == 0
    assert result.skipped == 2
    assert result.rejected == 2
    assert result.quarantine == [
        {"row": 1, "id": "P001", "reason": "duplicate patient_id"},
        {"row": 2, "id": "P002", "reason": "duplicate patient_id"},
    ]


def test_ingest_does_not_write_ingest_log(db, sample_df):
    ingest_dataframe(db, sample_df)
    assert cs.get_ingest_log(db) == []


def test_parse_upload_date_explicit_format():
    assert parse_upload_date("2026-10-05") == date(2026, 10, 5)


@pytest.mark.parametrize("text", ["05/10/2026", "Oct 5", "2026-13-01", ""])
def test_parse_upload_date_never_guesses(text):
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_upload_date(text)


def test_header_spaces_stripped(db, sample_df, tmp_path):
    path = tmp_path / "spaced.csv"
    spaced = sample_df.rename(columns=lambda c: f"   {c}  ")
    spaced.to_csv(path, index=False)
    df = read_patient_csv(path)
    assert tuple(df.columns) == REQUIRED_COLUMNS
    assert ingest_dataframe(db, df).accepted == 4


def test_bom_file_read(db, sample_df, tmp_path):
    path = tmp_path / "excel.csv"
    sample_df.to_csv(path, index=False, encoding="utf-8-sig")
    assert path.read_bytes().startswith(codecs.BOM_UTF8)
    df = read_patient_csv(path)
    assert df.columns[0] == "patient_id"
    assert ingest_dataframe(db, df).accepted == 4


def test_missing_column_has_readable_reason(db, sample_df):
    result = ingest_dataframe(db, sample_df.drop(columns=["patient_id"]))
    assert result.accepted == 0
    assert result.rejected == 4
    assert {q["reason"] for q in result.quarantine} == {
        "Missing column: patient_id"
    }
    assert {q["id"] for q in result.quarantine} == {"N/A"}
    assert cs.get_all_patients(db) == []


def test_missing_columns_listed_sorted(db, sample_df):
    result = ingest_dataframe(db, sample_df.drop(columns=["name", "city"]))
    reasons = {q["reason"] for q in result.quarantine}
    assert reasons == {"Missing columns: city, name"}
