"""Tests for get_symbol_context and get_symbol_references MCP queries."""

from pathlib import Path

from src.codeparse_mcp.symbol_context import get_symbol_context
from src.codeparse_mcp.symbol_references import get_symbol_references
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


def test_symbol_context_definition_only(tmp_path: Path) -> None:
    root = _index(tmp_path)
    db = CodeDB(root)
    try:
        out = get_symbol_context(db, "pkg.target.helper")
        assert "## Code Definition" in out
        assert "## References" in out
        assert "Calls: 2" in out
        assert "Access: 0" in out
        assert "Type Annotations: 0" in out
        assert "pkg/user.py" not in out
        assert "tests/test_target.py" not in out
        assert "## Calls" not in out
    finally:
        db.close()


def test_symbol_references_lists_calls_with_counts(tmp_path: Path) -> None:
    root = _index(tmp_path)
    db = CodeDB(root)
    try:
        out = get_symbol_references(db, "pkg.target.helper")
        assert "References of pkg.target.helper" in out
        assert "total" in out
        assert "pkg/user.py" in out
        assert "tests/test_target.py" in out
        assert "## Calls" in out
        assert "  • L" in out
        assert "pkg/user.py:" not in out
        assert "(" in out  # kind and/or file counts
    finally:
        db.close()


def test_symbol_references_none(tmp_path: Path) -> None:
    root = _index(tmp_path)
    db = CodeDB(root)
    try:
        out = get_symbol_references(db, "pkg.target.missing")
        assert out == "No references to pkg.target.missing were found."
    finally:
        db.close()
