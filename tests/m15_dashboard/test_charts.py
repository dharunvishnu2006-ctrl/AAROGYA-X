import pandas as pd
from aarogya.m15_dashboard.charts import plot_age_distribution


def test_plot_returns_figure(sample_csv):
    import matplotlib

    df = pd.read_csv(sample_csv)
    fig = plot_age_distribution(df)
    assert isinstance(fig, matplotlib.figure.Figure)
