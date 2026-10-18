"""Dashboard charts: theme-neutral, counts read from cohort_stats.

Figures are transparent and use mid-tone ink, so the same image
reads on Streamlit's light and dark themes.
"""

from matplotlib.figure import Figure

from aarogya.m6_risk.cohort_stats import (
    RISK_LEVELS,
    add_risk_level,
    city_counts,
)

# Use mid-tone ink for both themes
INK = "#808080"
BAR_COLOR = "#2a78d6"
# Use mid-tone grey for free beds
FREE_COLOR = "#b0b0b0"
# Size donut small; body-size text
DONUT_SIZE = (3.6, 1.5)
DONUT_FONT = 11
# Use CVD-safe slots, validated all-pairs
RISK_STYLE = {
    "Low": {"color": "#2a78d6", "marker": "o"},
    "Medium": {"color": "#1baf7a", "marker": "s"},
    "High": {"color": "#eb6834", "marker": "^"},
}


def _apply_theme(fig, ax):
    """Makes figure transparent with mid-tone ink."""
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")
    ax.title.set_color(INK)
    ax.xaxis.label.set_color(INK)
    ax.yaxis.label.set_color(INK)
    ax.tick_params(colors=INK)
    for spine in ax.spines.values():
        spine.set_color(INK)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    legend = ax.get_legend()
    if legend is not None:
        legend.get_frame().set_alpha(0.0)
        for text in legend.get_texts():
            text.set_color(INK)
        legend.get_title().set_color(INK)


def plot_age_distribution(df):
    # Avoid pyplot; GUI backends deadlock threads
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    ax.hist(
        df["age"], bins=10, color=BAR_COLOR, edgecolor="none", rwidth=0.9
    )
    ax.set_title("Patient Age Distribution")
    ax.set_xlabel("Age")
    ax.set_ylabel("Count")
    _apply_theme(fig, ax)
    return fig


def plot_bmi_vs_age(df):
    if "risk_level" not in df.columns:
        df = add_risk_level(df)
    # Avoid pyplot; GUI backends deadlock threads
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    for level in RISK_LEVELS:
        rows = df[df["risk_level"] == level]
        style = RISK_STYLE[level]
        ax.scatter(
            rows["age"],
            rows["bmi"],
            s=64,
            c=style["color"],
            marker=style["marker"],
            alpha=0.85,
            label=f"{level} risk",
        )
    ax.set_title("BMI vs Age by Risk Level")
    ax.set_xlabel("Age")
    ax.set_ylabel("BMI")
    ax.legend(
        title="Risk level", loc="upper left", bbox_to_anchor=(1.01, 1)
    )
    _apply_theme(fig, ax)
    return fig


def format_occupancy(pct):
    """Formats a rate for display; None (0 beds) shows a dash."""
    return "—" if pct is None else f"{pct:.1f}%"


def plot_occupancy_donut(occupied, available, pct):
    """Draws occupied vs available beds; real % in the centre.

    Small and wide: ring on the left, legend on the right. Show it
    with width=donut_width_px(fig) so it is never stretched.
    """
    # Avoid pyplot; GUI backends deadlock threads
    fig = Figure(figsize=DONUT_SIZE)
    # Keep ring in left 40%
    ax = fig.add_axes((0.0, 0.0, 0.4, 1.0))
    sizes = [occupied, available]
    # Draw empty ring for zero beds
    if sum(sizes) == 0:
        sizes = [0, 1]
    ax.pie(
        sizes,
        colors=[BAR_COLOR, FREE_COLOR],
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.32, "edgecolor": "none"},
    )
    ax.text(
        0,
        0,
        format_occupancy(pct),
        ha="center",
        va="center",
        fontsize=DONUT_FONT,
        fontweight="bold",
        color=INK,
    )
    ax.legend(
        [f"Occupied ({occupied})", f"Available ({available})"],
        loc="center left",
        bbox_to_anchor=(1.1, 0.5),
        fontsize=DONUT_FONT,
        frameon=False,
    )
    ax.set_aspect("equal")
    _apply_theme(fig, ax)
    return fig


def donut_width_px(fig):
    """Returns the figure's natural width in pixels."""
    return int(fig.get_figwidth() * fig.dpi)


def plot_city_patient_count(df):
    # Avoid pyplot; GUI backends deadlock threads
    fig = Figure(figsize=(8, 4))
    ax = fig.subplots()
    counts = city_counts(df)
    labels = counts.index.str.title()
    ax.bar(labels, counts.values, color=BAR_COLOR, width=0.8)
    ax.set_title("Patients per City")
    ax.set_xlabel("City")
    ax.set_ylabel("Count")
    ax.tick_params(axis="x", labelrotation=45)
    _apply_theme(fig, ax)
    fig.tight_layout()
    return fig
