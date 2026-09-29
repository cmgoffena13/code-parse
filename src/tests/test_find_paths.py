"""Tests for find_paths MCP query."""

from pathlib import Path

from src.codeparse_mcp.find_paths import _normalize_glob, find_paths
from src.db import CodeDB
from src.processor import CodeProcessor


def _index(root: Path) -> None:
    (root / ".gitignore").write_text("# test fixture\n", encoding="utf-8")
    pkg = root / "pkg"
    core = pkg / "core"
    core.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (core / "__init__.py").write_text("", encoding="utf-8")
    (core / "dialect.py").write_text(
        "def format_model() -> None:\n    pass\n",
        encoding="utf-8",
    )
    (core / "other.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "cli_main.py").write_text(
        "def main() -> None:\n    pass\n", encoding="utf-8"
    )
    tests = root / "tests"
    tests.mkdir()
    (tests / "test_dialect.py").write_text(
        "def test_format_model() -> None:\n    pass\n",
        encoding="utf-8",
    )
    db = CodeDB(root)
    CodeProcessor(db, root).process()
    db.close()


def test_normalize_glob_substring_and_starstar() -> None:
    assert _normalize_glob("dialect") == "*dialect*"
    assert _normalize_glob("**/cli/*.py") == "*/cli/*.py"
    assert _normalize_glob("*dialect*") == "*dialect*"
    assert _normalize_glob("  ") == ""


def test_find_paths_substring(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = find_paths(db, "dialect")
        assert "pkg/core/dialect.py" in out
        assert "other.py" not in out
        assert "tests/test_dialect.py" not in out
    finally:
        db.close()


def test_find_paths_include_tests(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = find_paths(db, "dialect", include_tests=True)
        assert "pkg/core/dialect.py" in out
        assert "tests/test_dialect.py" in out
    finally:
        db.close()


def test_find_paths_glob(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = find_paths(db, "pkg/core/*.py")
        assert "pkg/core/dialect.py" in out
        assert "pkg/core/other.py" in out
        assert "cli_main.py" not in out
    finally:
        db.close()


def test_find_paths_directories(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        out = find_paths(db, "pkg/core")
        assert "pkg/core/" in out
    finally:
        db.close()


def test_find_paths_empty(tmp_path: Path) -> None:
    _index(tmp_path)
    db = CodeDB(tmp_path)
    try:
        assert "pattern is empty" in find_paths(db, "  ")
    finally:
        db.close()
