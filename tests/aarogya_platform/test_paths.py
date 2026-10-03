import importlib

from aarogya.platform import paths


def test_root_is_repository_root():
    assert paths.ROOT.is_absolute()
    assert (paths.ROOT / "app.py").is_file()
    assert (paths.ROOT / "aarogya").is_dir()


def test_every_path_is_absolute_under_root():
    for p in (
        paths.DATA_DIR,
        paths.DB_PATH,
        paths.SEED_CSV,
        paths.LOG_DIR,
        paths.LOG_FILE,
    ):
        assert p.is_absolute()
        assert p.is_relative_to(paths.ROOT)


def test_seed_csv_exists():
    assert paths.SEED_CSV.is_file()


def test_paths_ignore_working_directory(tmp_path, monkeypatch):
    before = paths.DB_PATH
    monkeypatch.chdir(tmp_path)
    reloaded = importlib.reload(paths)
    assert reloaded.DB_PATH == before
    assert reloaded.ROOT != tmp_path
