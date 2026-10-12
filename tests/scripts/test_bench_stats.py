"""bench_stats.py: both methods agree; timings are not asserted."""

import importlib.util
import math

import pandas as pd
import pytest

from aarogya.platform import paths

BENCH_PATH = paths.ROOT / "scripts" / "bench_stats.py"


@pytest.fixture
def bench():
    spec = importlib.util.spec_from_file_location("bench", BENCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_loop_matches_hand_values(bench):
    values = [20.0, 22.0, 24.0, 26.0, 28.0]
    assert bench.loop_mean(values) == 24.0
    assert bench.loop_std(values) == pytest.approx(math.sqrt(10))


def test_loop_and_vectorised_agree(bench):
    frame = bench.synthetic_rows(500)
    columns = {v: list(map(float, frame[v])) for v in bench.VITALS}
    looped = bench.run_loop(columns)
    vectorised = bench.run_vectorised(frame)
    for vital in bench.VITALS:
        assert looped[vital] == pytest.approx(vectorised[vital], abs=1e-9)


def test_synthetic_rows_fixed_seed(bench):
    first = bench.synthetic_rows(100)
    pd.testing.assert_frame_equal(first, bench.synthetic_rows(100))
    assert first["bmi"].between(17.0, 40.0).all()
    assert first["bp_systolic"].between(100, 190).all()
    assert first["sugar_fasting"].between(70, 250).all()


def test_main_prints_both_sizes(bench, capsys):
    results = bench.main(["200"])
    out = capsys.readouterr().out
    assert [(r[0], r[1]) for r in results] == [
        ("sample", 50),
        ("synthetic", 200),
    ]
    assert "loop ms" in out and "vector ms" in out
