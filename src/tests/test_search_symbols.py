"""Tests for search_symbols MCP query."""

from pathlib import Path

from src.codeparse_mcp.search_symbols import search_symbols
from src.db import CodeDB
from src.processor import CodeProcessor


def _index(root: Path) -> None:
    (root / ".gitignore").write_text("# test fixture\n", encoding="utf-8")
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "prod.py").write_text(
        "def format_model() -> None:\n    pass\n",
        encoding="utf-8",
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_prod.py").write_text(
        "def test_format_model() -> None:\n    pass\n",
        encoding="utf-8",
    )
    db = CodeDB(root)
    CodeProcessor(db, root).process()
    db.close()


def test_search_symbols_excludes_is_test_by_default(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = search_symbols(db, "format_model", limit=20)
        assert "pkg/prod.py" in out
        assert "format_model" in out
        assert "test_format_model" not in out
    finally:
        db.close()


def test_search_symbols_include_tests(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = search_symbols(db, "format_model", limit=20, include_tests=True)
        assert "pkg/prod.py" in out
        assert "test_format_model" in out
    finally:
        db.close()
