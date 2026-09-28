import sys
from pathlib import Path

import pytest

from src.app import main


def test_version_flag_prints_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["cbp", "--version"])
    assert main() == 0
    out = capsys.readouterr().out
    assert "cbp Version:" in out
    assert "0.1.0" in out


def test_info_flag_prints_paths_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "codebase-parser-config"
    monkeypatch.setenv("CODEBASE_PARSER_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(sys, "argv", ["cbp", "--info"])
    assert main() == 0
    out = capsys.readouterr().out
    assert "CLI Path:" in out
    assert "Config Directory:" in out
    assert str(config_dir) in out


def test_cwd_missing_directory_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    missing = tmp_path / "no-such-dir"
    monkeypatch.setattr(sys, "argv", ["cbp", "--cwd", str(missing)])
    assert main() == 1
    err = capsys.readouterr().err
    assert "Not a directory" in err
