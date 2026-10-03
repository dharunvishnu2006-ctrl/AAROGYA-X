"""check.py logic with subprocess mocked; real tools never run here."""

import importlib.util
import subprocess

import pytest

from aarogya.platform import paths

CHECK_PATH = paths.ROOT / "scripts" / "check.py"


@pytest.fixture
def check():
    spec = importlib.util.spec_from_file_location("check", CHECK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_runner(failing):
    calls = []

    def _run(args):
        calls.append(args)
        code = 1 if args[0] in failing else 0
        return subprocess.CompletedProcess(args, code, "out", "")

    return _run, calls


def test_all_pass_exits_zero(check, monkeypatch, capsys):
    runner, calls = _fake_runner(failing=set())
    monkeypatch.setattr(check, "run_tool", runner)
    assert check.main([]) == 0
    lines = capsys.readouterr().out.splitlines()
    names = ["black", "flake8", "mypy", "bandit", "pytest"]
    assert [ln.split()[0] for ln in lines[:5]] == names
    assert all(ln.split()[1] == "PASS" for ln in lines[:5])
    assert lines[5] == "check: all PASS"
    assert [c[0] for c in calls] == names


def test_one_failure_exits_non_zero(check, monkeypatch, capsys):
    runner, calls = _fake_runner(failing={"black"})
    monkeypatch.setattr(check, "run_tool", runner)
    assert check.main([]) == 1
    out = capsys.readouterr().out
    assert "black    FAIL" in out
    assert "check: FAIL (black)" in out
    assert len(calls) == 5


def test_every_tool_runs_from_root_with_this_python(check, monkeypatch):
    seen = {}

    def _fake_run(cmd, **kwargs):
        seen["cmd"], seen["cwd"] = cmd, kwargs["cwd"]
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(check.subprocess, "run", _fake_run)
    check.run_tool(["flake8"])
    assert seen["cmd"][:3] == [check.sys.executable, "-m", "flake8"]
    assert seen["cwd"] == paths.ROOT
