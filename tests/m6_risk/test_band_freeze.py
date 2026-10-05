"""Risk bands of the 50 sample patients, frozen before v1.1 B2.

The expected bands were computed from the pre-refactor code. Any
change to a band here is a clinical change and must be reviewed.
"""

import pandas as pd

from aarogya.m1_emr.ingest import row_to_patient
from aarogya.m6_risk.analytics import score_patient_risk
from aarogya.m6_risk.scoring import ThresholdRiskScorer
from aarogya.platform import paths

FROZEN_BANDS = {
    "P001": "Medium",
    "P002": "High",
    "P003": "High",
    "P004": "High",
    "P005": "Medium",
    "P006": "High",
    "P007": "High",
    "P008": "High",
    "P009": "Medium",
    "P010": "High",
    "P011": "High",
    "P012": "High",
    "P013": "High",
    "P014": "High",
    "P015": "Medium",
    "P016": "High",
    "P017": "High",
    "P018": "High",
    "P019": "Medium",
    "P020": "Medium",
    "P021": "High",
    "P022": "High",
    "P023": "High",
    "P024": "High",
    "P025": "High",
    "P026": "High",
    "P027": "High",
    "P028": "High",
    "P029": "Medium",
    "P030": "High",
    "P031": "Low",
    "P032": "High",
    "P033": "High",
    "P034": "High",
    "P035": "High",
    "P036": "High",
    "P037": "High",
    "P038": "High",
    "P039": "Medium",
    "P040": "Medium",
    "P041": "High",
    "P042": "Medium",
    "P043": "Medium",
    "P044": "High",
    "P045": "Medium",
    "P046": "High",
    "P047": "Medium",
    "P048": "Medium",
    "P049": "High",
    "P050": "Medium",
}


def _sample_patients():
    df = pd.read_csv(paths.SEED_CSV)
    return [row_to_patient(row) for _, row in df.iterrows()]


def test_sample_covers_all_frozen_ids():
    ids = [p.patient_id for p in _sample_patients()]
    assert sorted(ids) == sorted(FROZEN_BANDS)


def test_bands_unchanged_via_score_patient_risk():
    bands = {
        p.patient_id: score_patient_risk(p) for p in _sample_patients()
    }
    assert bands == FROZEN_BANDS


def test_bands_unchanged_via_threshold_scorer():
    scorer = ThresholdRiskScorer()
    bands = {p.patient_id: scorer.score(p) for p in _sample_patients()}
    assert bands == FROZEN_BANDS
