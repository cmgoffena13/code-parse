"""Tests for search_symbols MCP query."""

import shutil
from pathlib import Path

from src.codeparse_mcp.search_symbols import search_symbols
from src.db import CodeDB
from src.processor import CodeProcessor


def _index(tmp_path: Path, python_fixtures_dir: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(python_fixtures_dir / "search_symbols", root)
    db = CodeDB(root)
    CodeProcessor(db, root).process()
    db.close()
    return root


def test_search_symbols_excludes_is_test_by_default(
    tmp_path: Path, python_fixtures_dir: Path
) -> None:
    root = _index(tmp_path, python_fixtures_dir)
    db = CodeDB(root)
    try:
        out = search_symbols(db, "format_model", limit=20)
        assert "pkg/prod.py" in out
        assert "format_model" in out
        assert "test_format_model" not in out
    finally:
        db.close()


def test_search_symbols_include_tests(
    tmp_path: Path, python_fixtures_dir: Path
) -> None:
    root = _index(tmp_path, python_fixtures_dir)
    db = CodeDB(root)
    try:
        out = search_symbols(db, "format_model", limit=20, include_tests=True)
        assert "pkg/prod.py" in out
        assert "test_format_model" in out
    finally:
        db.close()
