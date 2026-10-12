"""Times a plain Python loop vs pandas for mean and std.

Both sides compute mean and sample std (ddof=1) of the four vitals
on the same rows. Each side runs REPEATS times; the median run is
reported. Timings are printed exactly as measured.
Usage: python scripts/bench_stats.py
"""

import math
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SEED_CSV = ROOT / "data" / "patients_sample.csv"
VITALS = ["bmi", "bp_systolic", "bp_diastolic", "sugar_fasting"]
REPEATS = 20
SEED = 42
SYNTHETIC_ROWS = 50_000


def loop_mean(values):
    total = 0.0
    for value in values:
        total += value
    return total / len(values)


def loop_std(values):
    mean = loop_mean(values)
    squares = 0.0
    for value in values:
        squares += (value - mean) ** 2
    return math.sqrt(squares / (len(values) - 1))


def run_loop(columns):
    """Returns (mean, std) per vital, loop style."""
    return {v: (loop_mean(c), loop_std(c)) for v, c in columns.items()}


def run_vectorised(frame):
    """Returns (mean, std) per vital, pandas style."""
    return {v: (frame[v].mean(), frame[v].std()) for v in VITALS}


def synthetic_rows(n, seed=SEED):
    """Builds n rows in generate_data.py ranges."""
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "bmi": np.round(rng.uniform(17.0, 40.0, n), 1),
            "bp_systolic": rng.integers(100, 191, n),
            "bp_diastolic": rng.integers(60, 111, n),
            "sugar_fasting": rng.integers(70, 251, n),
        }
    )


def median_seconds(func, arg, repeats=REPEATS):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        func(arg)
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def bench(frame, repeats=REPEATS):
    """Returns (loop_s, vectorised_s) after checking agreement."""
    columns = {v: [float(x) for x in frame[v]] for v in VITALS}
    looped = run_loop(columns)
    vectorised = run_vectorised(frame)
    for vital in VITALS:
        assert np.allclose(looped[vital], vectorised[vital]), vital
    loop_s = median_seconds(run_loop, columns, repeats)
    vec_s = median_seconds(run_vectorised, frame, repeats)
    return loop_s, vec_s


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    synthetic_n = int(argv[0]) if argv else SYNTHETIC_ROWS
    inputs = [
        ("sample", pd.read_csv(SEED_CSV)),
        ("synthetic", synthetic_rows(synthetic_n)),
    ]
    print(
        f"mean + std of {len(VITALS)} vitals, "
        f"median of {REPEATS} runs, seed {SEED}"
    )
    print(f"{'input':<10} {'rows':>7} {'loop ms':>10} {'vector ms':>10}")
    results = []
    for label, frame in inputs:
        loop_s, vec_s = bench(frame)
        results.append((label, len(frame), loop_s, vec_s))
        print(
            f"{label:<10} {len(frame):>7} "
            f"{loop_s * 1000:>10.3f} {vec_s * 1000:>10.3f}"
        )
    return results


if __name__ == "__main__":
    main()
