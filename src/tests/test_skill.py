import runpy
from pathlib import Path

import pytest

from src.codeparse_mcp.skill import generate_skill


def test_generate_skill_defaults_to_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    path = generate_skill()
    assert path == tmp_path / ".claude" / "skills" / "codeparse" / "SKILL.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "get_symbol_context" in text
    assert "get_file_overview" in text


def test_generate_skill_writes_under_explicit_root(tmp_path: Path) -> None:
    path = generate_skill(tmp_path)
    assert path == tmp_path / ".claude" / "skills" / "codeparse" / "SKILL.md"
    assert path.is_file()


def test_skill_module_main_prints_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    runpy.run_module("src.codeparse_mcp.skill", run_name="__main__")
    out = capsys.readouterr().out
    assert "SKILL.md" in out
