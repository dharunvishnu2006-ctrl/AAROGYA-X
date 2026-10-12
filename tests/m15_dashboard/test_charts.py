import re

import pandas as pd
import pytest
from matplotlib.colors import to_hex, to_rgba

from aarogya.m15_dashboard import charts
from aarogya.m15_dashboard.charts import plot_age_distribution
from aarogya.m6_risk.cohort_stats import add_risk_level, city_counts
from aarogya.platform import paths

CHART_FUNCS = [
    charts.plot_age_distribution,
    charts.plot_bmi_vs_age,
    charts.plot_city_patient_count,
]


def test_plot_returns_figure(sample_csv):
    import matplotlib

    df = pd.read_csv(sample_csv)
    fig = plot_age_distribution(df)
    assert isinstance(fig, matplotlib.figure.Figure)


@pytest.fixture
def seed_df():
    return pd.read_csv(paths.SEED_CSV)


def test_city_chart_one_bar_per_city(seed_df):
    ax = charts.plot_city_patient_count(seed_df).axes[0]
    counts = city_counts(seed_df)
    assert len(ax.patches) == len(counts) == 10
    heights = [bar.get_height() for bar in ax.patches]
    assert heights == list(counts.values)


def test_city_chart_merges_spaced_names(sample_df):
    sample_df.loc[0, "city"] = " delhi"
    ax = charts.plot_city_patient_count(sample_df).axes[0]
    labels = [t.get_text() for t in ax.get_xticklabels()]
    assert sorted(labels) == ["Delhi", "Mumbai", "Pune"]
    assert max(bar.get_height() for bar in ax.patches) == 2


def test_age_histogram_title_and_total(seed_df):
    ax = charts.plot_age_distribution(seed_df).axes[0]
    assert ax.get_title() == "Patient Age Distribution"
    assert sum(bar.get_height() for bar in ax.patches) == len(seed_df)


def test_scatter_series_per_risk_level(seed_df):
    ax = charts.plot_bmi_vs_age(seed_df).axes[0]
    levels = add_risk_level(seed_df)["risk_level"].value_counts()
    labels = [t.get_text() for t in ax.get_legend().get_texts()]
    assert labels == ["Low risk", "Medium risk", "High risk"]
    sizes = [len(col.get_offsets()) for col in ax.collections]
    assert sizes == [levels[lv] for lv in ("Low", "Medium", "High")]


def test_scatter_second_cue_and_distinct_colours(seed_df):
    ax = charts.plot_bmi_vs_age(seed_df).axes[0]
    # Compare drawn marker outlines, not config
    shapes = {len(c.get_paths()[0].vertices) for c in ax.collections}
    colours = {to_hex(c.get_facecolor()[0]) for c in ax.collections}
    assert len(shapes) == 3
    assert len(colours) == 3


def test_scatter_ignores_gender(seed_df):
    flipped = seed_df.assign(
        gender=seed_df["gender"].map({"Male": "Female", "Female": "Male"})
    )
    ax_a = charts.plot_bmi_vs_age(seed_df).axes[0]
    ax_b = charts.plot_bmi_vs_age(flipped).axes[0]
    colours_a = [to_hex(c.get_facecolor()[0]) for c in ax_a.collections]
    colours_b = [to_hex(c.get_facecolor()[0]) for c in ax_b.collections]
    assert colours_a == colours_b


@pytest.mark.parametrize("plot", CHART_FUNCS)
def test_chart_is_theme_neutral(seed_df, plot):
    fig = plot(seed_df)
    ax = fig.axes[0]
    assert fig.patch.get_alpha() == 0.0
    assert to_rgba(ax.get_facecolor())[3] == 0.0
    ink = to_hex(charts.INK)
    assert to_hex(ax.title.get_color()) == ink
    assert to_hex(ax.xaxis.label.get_color()) == ink
    assert to_hex(ax.yaxis.label.get_color()) == ink


def test_every_chart_has_a_caller():
    app_src = (paths.ROOT / "app.py").read_text(encoding="utf-8")
    public = [n for n in dir(charts) if n.startswith("plot_")]
    assert sorted(public) == sorted(f.__name__ for f in CHART_FUNCS)
    for name in public:
        assert re.search(rf"\b{name}\(", app_src), name


@pytest.mark.parametrize("plot", CHART_FUNCS)
def test_chart_avoids_pyplot_state(seed_df, plot):
    import matplotlib.pyplot as plt

    # Guard against Streamlit thread deadlock
    before = plt.get_fignums()
    plot(seed_df)
    assert plt.get_fignums() == before
