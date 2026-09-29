"""Tests for find_importers MCP query."""

from pathlib import Path

import pytest

from src.codeparse_mcp.find_importers import find_importers
from src.db import CodeDB
from src.processor import CodeProcessor


@pytest.fixture
def indexed_import_pair(tmp_path: Path) -> Path:
    (tmp_path / ".gitignore").write_text("# test fixture\n", encoding="utf-8")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "target.py").write_text(
        '"""Target module."""\n\ndef helper() -> int:\n    return 1\n',
        encoding="utf-8",
    )
    (pkg / "importer.py").write_text(
        "from pkg.target import helper\n\n\ndef run() -> int:\n    return helper()\n",
        encoding="utf-8",
    )
    (tmp_path / "other.py").write_text(
        "from pkg.target import helper as h\n",
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


def test_find_importers_by_path(indexed_import_pair: Path) -> None:
    db = CodeDB(indexed_import_pair)
    try:
        by_path = find_importers(db, "pkg/target.py")

        assert "pkg/importer.py" in by_path
        assert "other.py" in by_path
        assert "helper" in by_path
        assert "Importers of pkg/target.py" in by_path
        assert "Legend: • = Import" in by_path
        assert "1S" not in by_path
        assert "  • pkg/importer.py:" in by_path
        assert " - " in by_path
        assert "tests/test_target.py" not in by_path

        dotted = find_importers(db, "pkg.target")
        assert "No indexed file matches" in dotted
    finally:
        db.close()


def test_find_importers_include_tests(indexed_import_pair: Path) -> None:
    db = CodeDB(indexed_import_pair)
    try:
        out = find_importers(db, "pkg/target.py", include_tests=True)
        assert "pkg/importer.py" in out
        assert "tests/test_target.py" in out
    finally:
        db.close()


def test_find_importers_missing_target(indexed_import_pair: Path) -> None:
    db = CodeDB(indexed_import_pair)
    try:
        out = find_importers(db, "pkg/missing.py")
        assert "No indexed file matches" in out
    finally:
        db.close()


def test_find_importers_empty_input(indexed_import_pair: Path) -> None:
    db = CodeDB(indexed_import_pair)
    try:
        assert "file_path is empty" in find_importers(db, "  ")
    finally:
        db.close()
