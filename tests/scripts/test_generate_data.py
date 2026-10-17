"""generate_data.py: fixed seed; stays obey the rules; patients kept."""

import importlib.util
import shutil

import pandas as pd
import pytest

from aarogya.m1_emr import clinical_store as cs
from aarogya.m1_emr.bootstrap import bootstrap_store
from aarogya.m2_his.hospitals import HOSPITAL_NETWORK
from aarogya.m2_his.stays import count_stays
from aarogya.platform import paths

GEN_PATH = paths.DATA_DIR / "generate_data.py"


@pytest.fixture
def gen():
    spec = importlib.util.spec_from_file_location("gen", GEN_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def data_dir(tmp_path):
    shutil.copy(paths.SEED_CSV, tmp_path / paths.SEED_CSV.name)
    return tmp_path


def _sample_ids():
    return pd.read_csv(paths.SEED_CSV, dtype=str)["patient_id"].tolist()


def test_same_seed_same_stays(gen):
    first = gen.generate_stays(_sample_ids())
    second = gen.generate_stays(_sample_ids())
    pd.testing.assert_frame_equal(first, second)


def test_other_seed_other_stays(gen):
    first = gen.generate_stays(_sample_ids(), seed=42)
    other = gen.generate_stays(_sample_ids(), seed=7)
    assert not first.equals(other)


def test_stays_reference_sample_patients(gen):
    stays = gen.generate_stays(_sample_ids())
    assert len(stays) > 0
    assert set(stays["patient_id"]) <= set(_sample_ids())
    known = {h.hospital_id for h in HOSPITAL_NETWORK}
    assert set(stays["hospital_id"]) <= known


def test_stays_never_break_rules(gen):
    stays = gen.generate_stays(_sample_ids())
    open_stays = stays[stays["discharged_at"] == ""]
    assert open_stays["patient_id"].is_unique
    beds = open_stays[["hospital_id", "ward", "bed"]]
    assert not beds.duplicated().any()
    closed = stays[stays["discharged_at"] != ""]
    admitted = pd.to_datetime(closed["admitted_at"])
    assert (pd.to_datetime(closed["discharged_at"]) > admitted).all()
    assert (stays["discharged_at"] == "").any()
    assert (stays["discharged_at"] != "").any()


def test_hospitals_come_from_network(gen):
    hospitals = gen.generate_hospitals()
    assert hospitals["hospital_id"].tolist() == [
        h.hospital_id for h in HOSPITAL_NETWORK
    ]


def test_default_run_keeps_patients_file(gen, data_dir):
    patients = data_dir / paths.SEED_CSV.name
    before = patients.read_bytes()
    assert gen.main([], data_dir=data_dir) == 0
    assert patients.read_bytes() == before
    assert (data_dir / paths.HOSPITALS_CSV.name).exists()
    assert (data_dir / paths.STAYS_CSV.name).exists()


def test_committed_csvs_match_generator(gen, data_dir):
    gen.main([], data_dir=data_dir)
    for name in (paths.HOSPITALS_CSV.name, paths.STAYS_CSV.name):
        fresh = pd.read_csv(data_dir / name, dtype=str)
        stored = pd.read_csv(paths.DATA_DIR / name, dtype=str)
        pd.testing.assert_frame_equal(fresh, stored)


def test_generated_seed_loads_without_refusals(tmp_path):
    db_path = tmp_path / "aarogya.db"
    bootstrap_store(
        db_path, paths.SEED_CSV, paths.HOSPITALS_CSV, paths.STAYS_CSV
    )
    expected = len(pd.read_csv(paths.STAYS_CSV))
    conn = cs.get_connection(str(db_path))
    try:
        assert count_stays(conn) == expected
    finally:
        conn.close()
