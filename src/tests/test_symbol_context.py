"""Tests for get_symbol_context MCP query."""

from pathlib import Path

from src.codeparse_mcp.symbol_context import get_symbol_context
from src.db import CodeDB
from src.processor import CodeProcessor


def _index(tmp_path: Path) -> Path:
    (tmp_path / ".gitignore").write_text("# test fixture\n", encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "target.py").write_text(
        "def helper() -> int:\n    return 1\n",
        encoding="utf-8",
    )
    (pkg / "user.py").write_text(
        "from pkg.target import helper\n\n\ndef run() -> int:\n    return helper()\n",
        encoding="utf-8",
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_target.py").write_text(
        "from pkg.target import helper\n\n\ndef test_helper() -> None:\n    assert helper() == 1\n",
        encoding="utf-8",
    )
    db = CodeDB(tmp_path)
    CodeProcessor(db, tmp_path).process()
    db.close()
    return tmp_path


def test_symbol_context_definition_omits_references_by_default(tmp_path: Path) -> None:
    root = _index(tmp_path)
    db = CodeDB(root)
    try:
        out = get_symbol_context(db, "pkg.target.helper")
        assert "## Code Definition" in out
        assert "pkg/user.py" not in out
        assert "tests/test_target.py" not in out
        assert "## Calls" not in out
    finally:
        db.close()


def test_symbol_context_include_references_lists_all_refs(tmp_path: Path) -> None:
    root = _index(tmp_path)
    db = CodeDB(root)
    try:
        out = get_symbol_context(db, "pkg.target.helper", include_references=True)
        assert "pkg/user.py" in out
        assert "tests/test_target.py" in out
        assert "## Calls" in out
        assert "  • L" in out
        assert "pkg/user.py:" not in out
    finally:
        db.close()
