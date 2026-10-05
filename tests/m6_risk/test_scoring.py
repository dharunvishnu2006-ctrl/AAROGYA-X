import pytest

from aarogya.m6_risk.scoring import (
    RISK_RANK,
    RiskScorer,
    ThresholdRiskScorer,
)


def test_threshold_scorer_is_a_risk_scorer():
    assert isinstance(ThresholdRiskScorer(), RiskScorer)


def test_risk_scorer_is_abstract():
    with pytest.raises(TypeError):
        RiskScorer()  # type: ignore[abstract]


def test_risk_rank_puts_high_first():
    bands = sorted(RISK_RANK, key=RISK_RANK.__getitem__)
    assert bands == ["High", "Medium", "Low"]
