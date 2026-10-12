"""Cohort numbers of the 50 sample patients, frozen before v1.1 B3.

The expected values were computed from the pre-B3 code (dashboard
.mean() calls and analytics.calc_*). Any change here is a change to
a number a clinician reads and must be reviewed.
"""

import pandas as pd
import pytest

from aarogya.m6_risk.analytics import calc_avg_bmi
from aarogya.m6_risk.cohort_stats import city_counts, describe_vitals
from aarogya.platform import paths

FROZEN_CARDS = {
    "bp_systolic": "147.6",
    "sugar_fasting": "166.8",
    "bmi": "27.1",
}
FROZEN_AVG_BMI = {"mean": 27.1, "min": 17.5, "max": 38.8}
FROZEN_BP_MEDIAN = {"bp_systolic": 153.5, "bp_diastolic": 84.5}
FROZEN_SUGAR = {"mean": 166.82, "std": 50.53}
FROZEN_CITY_COUNTS = {
    "ahmedabad": 8,
    "mumbai": 7,
    "bangalore": 6,
    "chennai": 5,
    "kolkata": 5,
    "hyderabad": 5,
    "lucknow": 4,
    "pune": 4,
    "delhi": 3,
    "jaipur": 3,
}


@pytest.fixture
def seed_df():
    return pd.read_csv(paths.SEED_CSV)


def test_calc_avg_bmi_unchanged(seed_df):
    assert calc_avg_bmi(seed_df) == FROZEN_AVG_BMI


def test_card_means_unchanged(seed_df):
    stats = describe_vitals(seed_df)
    cards = {v: f"{stats.loc[v, 'mean']:.1f}" for v in FROZEN_CARDS}
    assert cards == FROZEN_CARDS


def test_bp_median_and_sugar_std_unchanged(seed_df):
    stats = describe_vitals(seed_df)
    median = {v: stats.loc[v, "median"] for v in FROZEN_BP_MEDIAN}
    sugar = stats.loc["sugar_fasting", ["mean", "std"]]
    assert median == FROZEN_BP_MEDIAN
    assert round(sugar["mean"], 2) == FROZEN_SUGAR["mean"]
    assert round(sugar["std"], 2) == FROZEN_SUGAR["std"]


def test_city_counts_unchanged(seed_df):
    counts = city_counts(seed_df)
    assert counts.to_dict() == FROZEN_CITY_COUNTS
