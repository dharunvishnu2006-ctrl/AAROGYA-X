"""make_diagrams.py writes both PNGs; never into the real docs/."""

import importlib.util

from aarogya.platform import paths

DIAGRAMS_PATH = paths.ROOT / "scripts" / "make_diagrams.py"
PNG_SIGNATURE = b"\x89PNG"


def test_creates_both_pngs(tmp_path):
    spec = importlib.util.spec_from_file_location("diagrams", DIAGRAMS_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main([], out_dir=tmp_path) == 0
    for name in ("architecture.png", "evolution.png"):
        path = tmp_path / name
        assert path.exists() and path.stat().st_size > 0
        assert path.read_bytes()[:4] == PNG_SIGNATURE
