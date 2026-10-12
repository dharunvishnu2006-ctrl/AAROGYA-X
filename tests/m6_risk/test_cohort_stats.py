"""cohort_stats against a 5-row table worked out by hand.

Hand workings (std uses n - 1; p90 sits at position
0.9 * (n - 1) = 3.6, linear interpolation):
  bmi:   sum sq dev 16+4+0+4+16 = 40, var 40/4, std sqrt(10)
  sbp:   dev -30,-20,-10,0,60 -> 5000/4 = 1250, p90 140+0.6*60
  dbp:   dev -10,-10,0,10,10 -> 400/4 = 100, std 10
  sugar: dev -20,-10,0,10,20 -> 1000/4 = 250, p90 120+0.6*10
"""

import math

import pandas as pd
import pytest

from aarogya.m6_risk import cohort_stats as cst
from aarogya.platform import paths
from tests.m6_risk.test_band_freeze import FROZEN_BANDS

HAND_ROWS = {
    "patient_id": ["P001", "P002", "P003", "P004", "P005"],
    "age": [25, 30, 44, 45, 60],
    "bmi": [20.0, 22.0, 24.0, 26.0, 28.0],
    "bp_systolic": [110.0, 120.0, 130.0, 140.0, 200.0],
    "bp_diastolic": [70.0, 70.0, 80.0, 90.0, 90.0],
    "sugar_fasting": [90.0, 100.0, 110.0, 120.0, 130.0],
    "city": ["Pune", " pune", "Delhi", "Delhi", "Chennai"],
}

BY_HAND = {
    "bmi": [5, 24.0, 24.0, math.sqrt(10), 22.0, 26.0, 27.2, 20.0, 28.0],
    "bp_systolic": [
        5,
        140.0,
        130.0,
        math.sqrt(1250),
        120.0,
        140.0,
        176.0,
        110.0,
        200.0,
    ],
    "bp_diastolic": [5, 80.0, 80.0, 10.0, 70.0, 90.0, 90.0, 70.0, 90.0],
    "sugar_fasting": [
        5,
        110.0,
        110.0,
        math.sqrt(250),
        100.0,
        120.0,
        126.0,
        90.0,
        130.0,
    ],
}


@pytest.fixture
def hand_df():
    return pd.DataFrame(HAND_ROWS)


@pytest.mark.parametrize("vital", cst.VITALS)
def test_describe_matches_hand_worked_values(hand_df, vital):
    row = cst.describe_vitals(hand_df).loc[vital]
    expected = dict(zip(cst.STAT_COLUMNS, BY_HAND[vital]))
    for stat, value in expected.items():
        assert row[stat] == pytest.approx(value), stat


def test_describe_shape_and_columns(hand_df):
    table = cst.describe_vitals(hand_df)
    assert list(table.index) == cst.VITALS
    assert list(table.columns) == cst.STAT_COLUMNS
    assert table["count"].dtype.kind == "i"


def test_describe_skips_missing_values(hand_df):
    hand_df.loc[4, "bmi"] = float("nan")
    row = cst.describe_vitals(hand_df).loc["bmi"]
    assert row["count"] == 4
    assert row["mean"] == pytest.approx(23.0)


def test_cohort_size(hand_df):
    assert cst.cohort_size(hand_df) == 5
    assert cst.cohort_size(hand_df.iloc[0:0]) == 0


def test_age_band_edges():
    df = pd.DataFrame({"age": [29, 30, 44, 45, 59, 60]})
    bands = list(cst.add_age_band(df)["age_band"])
    assert bands == ["<30", "30-44", "30-44", "45-59", "45-59", "60+"]


def test_add_age_band_leaves_input_alone(hand_df):
    cst.add_age_band(hand_df)
    assert "age_band" not in hand_df.columns


def test_risk_level_matches_frozen_bands():
    df = cst.add_risk_level(pd.read_csv(paths.SEED_CSV))
    levels = dict(zip(df["patient_id"], df["risk_level"]))
    assert levels == FROZEN_BANDS


def test_group_by_city_one_row_per_city(hand_df):
    table = cst.group_stats(hand_df, "city")
    assert len(table) == hand_df["city"].nunique()
    assert table[("bmi", "count")].sum() == len(hand_df)


def test_group_by_age_band_values(hand_df):
    table = cst.group_stats(cst.add_age_band(hand_df), "age_band")
    counts = table[("bmi", "count")].to_dict()
    assert counts == {"<30": 1, "30-44": 2, "45-59": 1, "60+": 1}
    # Expect bmi 22 and 24 here
    assert table.loc["30-44", ("bmi", "mean")] == pytest.approx(23.0)
    assert table.loc["30-44", ("bmi", "std")] == pytest.approx(math.sqrt(2))


def test_group_by_risk_level_counts_add_up():
    df = cst.add_risk_level(pd.read_csv(paths.SEED_CSV))
    table = cst.group_stats(df, "risk_level")
    counts = table[("bmi", "count")].to_dict()
    expected = pd.Series(FROZEN_BANDS).value_counts().to_dict()
    assert counts == expected


def test_city_counts_normalise_names(hand_df):
    counts = cst.city_counts(hand_df).to_dict()
    assert counts == {"pune": 2, "delhi": 2, "chennai": 1}
