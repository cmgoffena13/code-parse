import runpy
import sys
from pathlib import Path
from typing import Any

import pytest

from src.codeparse_mcp.skill import generate_skill


def test_generate_skill_claude_defaults_to_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    path = generate_skill("claude")
    assert path == tmp_path / ".claude" / "skills" / "codeparse" / "SKILL.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "get_symbol_context" in text
    assert "get_file_overview" in text


def test_generate_skill_claude_writes_under_explicit_root(tmp_path: Path) -> None:
    path = generate_skill("claude", root=tmp_path)
    assert path == tmp_path / ".claude" / "skills" / "codeparse" / "SKILL.md"
    assert path.is_file()


def test_generate_skill_cursor_writes_under_home_skills(tmp_path: Path) -> None:
    skills_base = tmp_path / "skills"
    path = generate_skill("cursor", cursor_skills_base=skills_base)
    assert path == skills_base / "codeparse" / "SKILL.md"
    assert path.is_file()
    assert "search_symbols" in path.read_text(encoding="utf-8")


def test_generate_skill_rejects_unknown_target() -> None:
    bad_target: Any = "vscode"
    with pytest.raises(ValueError, match="unknown skill target"):
        generate_skill(bad_target)


def test_skill_module_main_prints_path(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["skill", "claude"])
    runpy.run_module("src.codeparse_mcp.skill", run_name="__main__")
    out = capsys.readouterr().out
    assert "SKILL.md" in out


def test_skill_module_main_requires_target(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["skill"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("src.codeparse_mcp.skill", run_name="__main__")
    assert exc.value.code == 2
    assert "claude|cursor" in capsys.readouterr().err
