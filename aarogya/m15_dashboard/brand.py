"""Brand config for the Overview header. No Streamlit here.

The version always comes from docs/versions.json, so it is never
typed in by hand.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from aarogya.platform import paths

PathLike = Union[str, Path]
VERSIONS_FILE = paths.ROOT / "docs" / "versions.json"
RELEASED = "released"


@dataclass(frozen=True)
class Brand:
    name: str
    vision: str
    today_text: str
    accent: str


BRAND = Brand(
    name="AAROGYA X",
    vision="AI-powered healthcare platform",
    today_text=(
        "patient records, rule-based risk, beds and occupancy, "
        "FHIR export - synthetic data"
    ),
    accent="#15803D",
)


def current_version(path: PathLike = VERSIONS_FILE) -> str:
    """Returns the newest released version in versions.json."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    released = [
        v["version"] for v in data["versions"] if v["status"] == RELEASED
    ]
    if not released:
        raise ValueError("versions.json has no released version.")
    return released[-1]


def today_line(version: str, brand: Brand = BRAND) -> str:
    """Returns the Today line for one version."""
    return f"Today ({version}): {brand.today_text}"
