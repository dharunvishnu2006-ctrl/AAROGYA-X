from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.ingest import ingest_dataframe


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
