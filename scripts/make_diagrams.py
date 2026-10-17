"""Draws the v1.1 architecture and version roadmap as PNGs.

Uses matplotlib only. Version names and statuses come from
docs/versions.json; nothing about future versions is invented.
Usage: python scripts/make_diagrams.py
"""

import json
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib

# Render to files; no display needed
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.patches import FancyArrowPatch  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "diagrams"
VERSIONS_JSON = ROOT / "docs" / "versions.json"
ARCH_FILE = "architecture.png"
EVOLUTION_FILE = "evolution.png"
ROADMAP = ["v1.0", "v1.1", "v2", "v3", "v4", "v5", "v6"]
DPI = 150

INK = "#1f2933"
LINE = "#52606d"
INPUT = "#fde8c8"
CHECK = "#fbd5d5"
STORE = "#cfe3f7"
LOGIC = "#d5f0dc"
OUTPUT = "#e4dcf7"
SIDE = "#eceff1"
DONE = "#cfe3f7"

Point = Tuple[float, float]


def _box(
    ax: Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: Sequence[str] = (),
    color: str = STORE,
    dashed: bool = False,
    filled: bool = True,
) -> None:
    """Draws one rounded box with centred title and lines."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            facecolor=color if filled else "white",
            edgecolor=LINE,
            linewidth=1.6,
            linestyle="--" if dashed else "-",
        )
    )
    step = 0.3
    top = y + h / 2 + len(lines) * step / 2
    ax.text(
        x + w / 2,
        top,
        title,
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color=INK,
    )
    for i, line in enumerate(lines, start=1):
        ax.text(
            x + w / 2,
            top - i * step,
            line,
            ha="center",
            va="center",
            fontsize=10,
            color=INK,
        )


def _arrow(ax: Axes, start: Point, end: Point) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=18,
            linewidth=1.6,
            color=LINE,
        )
    )


def _canvas(width: float, height: float) -> Tuple[Any, Axes]:
    fig, ax = plt.subplots(figsize=(width, height), facecolor="white")
    ax.set_xlim(0, width)
    ax.set_ylim(0, height)
    ax.axis("off")
    return fig, ax


def draw_architecture(path: Path) -> None:
    """Saves the v1.1 data-flow diagram."""
    fig, ax = _canvas(16, 9)
    ax.text(
        8,
        8.6,
        "AAROGYA X v1.1 - architecture",
        ha="center",
        fontsize=16,
        fontweight="bold",
        color=INK,
    )
    _box(ax, 0.3, 4.0, 2.2, 1.4, "CSV input", ["upload or seed"], INPUT)
    _box(
        ax,
        3.0,
        3.6,
        2.6,
        2.2,
        "Validation",
        ["Patient model", "patient_id format", "bad rows -> quarantine"],
        CHECK,
    )
    _box(
        ax,
        6.1,
        3.0,
        2.8,
        3.4,
        "SQLite store",
        [
            "patients",
            "patient_corrections",
            "ingest_log",
            "hospitals",
            "stays",
        ],
        STORE,
    )
    _arrow(ax, (2.5, 4.7), (3.0, 4.7))
    _arrow(ax, (5.6, 4.7), (6.1, 4.7))

    # Lay out three lanes from store
    _box(
        ax, 9.4, 6.5, 2.1, 1.4, "cohort_stats", ["one stats module"], LOGIC
    )
    _box(ax, 9.4, 3.9, 2.1, 1.4, "Stay rules", ["stays.py"], LOGIC)
    _box(
        ax, 9.4, 1.3, 2.1, 1.4, "read_model", ["one view per route"], LOGIC
    )
    _box(
        ax,
        11.9,
        3.9,
        1.8,
        1.4,
        "Occupancy",
        ["open stays", "/ beds"],
        LOGIC,
    )
    _box(
        ax,
        13.9,
        6.3,
        2.0,
        1.8,
        "Streamlit",
        ["dashboard"],
        OUTPUT,
    )
    _box(
        ax,
        13.9,
        1.1,
        2.0,
        1.8,
        "Flask API",
        ["127.0.0.1 only", "no names"],
        OUTPUT,
    )
    _arrow(ax, (8.9, 6.0), (9.4, 7.2))
    _arrow(ax, (8.9, 4.6), (9.4, 4.6))
    _arrow(ax, (8.9, 3.4), (9.4, 2.0))
    _arrow(ax, (11.5, 7.2), (13.9, 7.2))
    _arrow(ax, (11.5, 4.6), (11.9, 4.6))
    _arrow(ax, (11.5, 2.0), (13.9, 2.0))
    _arrow(ax, (13.7, 5.1), (14.4, 6.3))
    _arrow(ax, (13.7, 4.1), (14.4, 2.9))

    _box(
        ax,
        0.3,
        0.5,
        5.3,
        1.6,
        "JSON logs + health check",
        ["counts only - no patient data"],
        SIDE,
    )
    fig.savefig(path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def load_versions(path: Path) -> Dict[str, Any]:
    """Reads the project's version list."""
    with open(path, encoding="utf-8") as handle:
        data: Dict[str, Any] = json.load(handle)
    return data


def _version_lines(entry: Optional[Dict[str, Any]]) -> List[str]:
    if entry is None:
        return []
    lines = textwrap.wrap(str(entry.get("name", "")), width=14)
    if entry.get("status") and entry.get("status") != "released":
        lines.append(f"({entry['status']})")
    return lines


def draw_evolution(path: Path, versions: Dict[str, Any]) -> None:
    """Saves the roadmap: released filled, later ones dashed."""
    by_version = {v["version"]: v for v in versions.get("versions", [])}
    fig, ax = _canvas(16, 4)
    title = f"{versions.get('project', 'AAROGYA X')} - version roadmap"
    ax.text(
        8,
        3.5,
        title,
        ha="center",
        fontsize=16,
        fontweight="bold",
        color=INK,
    )
    w, gap, x = 1.9, 0.35, 0.3
    for i, version in enumerate(ROADMAP):
        entry = by_version.get(version)
        released = entry is not None and entry.get("status") == "released"
        _box(
            ax,
            x,
            0.9,
            w,
            1.9,
            version,
            _version_lines(entry),
            DONE,
            dashed=not released,
            filled=released,
        )
        if i < len(ROADMAP) - 1:
            _arrow(ax, (x + w, 1.85), (x + w + gap, 1.85))
        x += w + gap
    ax.text(
        8,
        0.35,
        "filled = released    dashed = planned",
        ha="center",
        fontsize=10,
        color=LINE,
    )
    fig.savefig(path, dpi=DPI, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main(
    argv: Optional[List[str]] = None,
    out_dir: Path = OUT_DIR,
    versions_json: Path = VERSIONS_JSON,
) -> int:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    arch = out_dir / ARCH_FILE
    evolution = out_dir / EVOLUTION_FILE
    draw_architecture(arch)
    draw_evolution(evolution, load_versions(Path(versions_json)))
    print(f"Saved {arch}")
    print(f"Saved {evolution}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
