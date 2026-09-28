import sys
from pathlib import Path

import pytest

from src.utils import get_version


def test_get_version_reads_pyproject() -> None:
    assert get_version() == "0.1.0"


def test_get_version_frozen_with_meipass(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    meipass = tmp_path / "meipass"
    meipass.mkdir()
    (meipass / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "9.9.9"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)
    assert get_version() == "9.9.9"


def test_get_version_frozen_falls_back_to_exe_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    exe_dir = tmp_path / "dist"
    exe_dir.mkdir()
    (exe_dir / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    exe = exe_dir / "cbp"
    exe.write_text("x", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "empty-meipass"), raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert get_version() == "1.2.3"


def test_get_version_frozen_missing_meipass(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", None, raising=False)
    with pytest.raises(RuntimeError, match="_MEIPASS"):
        get_version()
