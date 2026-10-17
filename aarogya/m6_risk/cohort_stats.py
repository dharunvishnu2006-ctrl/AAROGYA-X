"""Cohort statistics: the one source for every dashboard number.

All maths is vectorised with pandas/NumPy. The only row loop is
add_risk_level, which reuses the clinical scorer so risk bands can
never drift from M6 scoring.
"""

import numpy as np
import pandas as pd

from aarogya.m6_risk.scoring import ThresholdRiskScorer

VITALS = ["bmi", "bp_systolic", "bp_diastolic", "sugar_fasting"]
STAT_COLUMNS = [
    "count",
    "mean",
    "median",
    "std",
    "p25",
    "p75",
    "p90",
    "min",
    "max",
]
GROUP_STATS = ["count", "mean", "median", "std"]
AGE_BAND_EDGES = [-np.inf, 30, 45, 60, np.inf]
AGE_BAND_LABELS = ["<30", "30-44", "45-59", "60+"]
RISK_LEVELS = ["Low", "Medium", "High"]
# Share one stateless scorer instance
_SCORER = ThresholdRiskScorer()


def cohort_size(df: pd.DataFrame) -> int:
    return int(len(df))


def describe_vitals(df: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per vital, one column per statistic."""
    vitals = df[VITALS].apply(pd.to_numeric, errors="coerce")
    basic = vitals.agg(["count", "mean", "median", "std", "min", "max"])
    pcts = vitals.quantile([0.25, 0.75, 0.90])
    pcts.index = ["p25", "p75", "p90"]
    table = pd.concat([basic, pcts]).T
    table["count"] = table["count"].astype(int)
    return table[STAT_COLUMNS]


def add_age_band(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy with an age_band column."""
    out = df.copy()
    out["age_band"] = pd.cut(
        out["age"],
        bins=AGE_BAND_EDGES,
        right=False,
        labels=AGE_BAND_LABELS,
    )
    return out


def age_band_of(age: int) -> str:
    """Returns one age's band; same cut as add_age_band."""
    band = pd.cut(
        [age],
        bins=AGE_BAND_EDGES,
        right=False,
        labels=AGE_BAND_LABELS,
    )[0]
    return str(band)


def add_risk_level(df: pd.DataFrame) -> pd.DataFrame:
    """Returns a copy with risk_level from the M6 scorer."""
    out = df.copy()
    # Reuse scorer; never duplicate thresholds
    levels = [_SCORER.score(row) for row in out.itertuples()]
    out["risk_level"] = pd.Categorical(levels, categories=RISK_LEVELS)
    return out


def group_stats(df: pd.DataFrame, by: str) -> pd.DataFrame:
    """Returns count/mean/median/std of vitals per group."""
    grouped = df.groupby(by, observed=True)[VITALS]
    return grouped.agg(GROUP_STATS)


def city_counts(df: pd.DataFrame) -> pd.Series:
    """Counts patients per normalised city name."""
    cities = df["city"].astype(str).str.strip().str.lower()
    return cities.value_counts()
