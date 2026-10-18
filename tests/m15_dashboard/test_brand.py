"""Brand config: version from versions.json, fixed band colour."""

import json
from pathlib import Path

import pytest

from aarogya.m15_dashboard import brand
from aarogya.platform import paths


def released_versions():
    data = json.loads(
        (paths.ROOT / "docs" / "versions.json").read_text(encoding="utf-8")
    )
    return [
        v["version"] for v in data["versions"] if v["status"] == "released"
    ]


def test_current_version_is_last_released():
    assert brand.current_version() == released_versions()[-1]


def test_version_follows_the_file(tmp_path):
    path = tmp_path / "versions.json"
    path.write_text(
        json.dumps(
            {
                "versions": [
                    {"version": "v1.1", "status": "released"},
                    {"version": "v9.9", "status": "released"},
                    {"version": "v10", "status": "next"},
                ]
            }
        ),
        encoding="utf-8",
    )
    version = brand.current_version(path)
    assert version == "v9.9"
    assert brand.today_line(version).startswith("Today (v9.9): ")


def test_no_released_version_raises(tmp_path):
    path = tmp_path / "versions.json"
    path.write_text('{"versions": []}', encoding="utf-8")
    with pytest.raises(ValueError):
        brand.current_version(path)


def test_today_line_uses_file_version():
    version = released_versions()[-1]
    line = brand.today_line(brand.current_version())
    assert line == f"Today ({version}): {brand.BRAND.today_text}"


def test_no_band_colours_left():
    fields = set(brand.Brand.__dataclass_fields__)
    assert not fields & {"band", "gold", "today_green"}


def test_brand_has_no_streamlit_or_logo():
    src = Path(brand.__file__).read_text(encoding="utf-8")
    assert "streamlit" not in src
    assert "logo" not in src.lower()
    assert "PIL" not in src
