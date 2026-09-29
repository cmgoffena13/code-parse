"""Tests for file-level is_test helpers."""

from pathlib import Path

from src.processor import file_path_is_test


def test_file_path_is_test_rules() -> None:
    assert file_path_is_test(Path("tests/core/test_foo.py"))
    assert file_path_is_test(Path("test_foo.py"))
    assert file_path_is_test(Path("pkg/foo_test.py"))
    assert file_path_is_test(Path("tests/conftest.py"))
    # Package named test (not tests/) is not a suite root.
    assert not file_path_is_test(Path("sqlmesh/core/test/definition.py"))
    assert not file_path_is_test(Path("sqlmesh/core/dialect.py"))
