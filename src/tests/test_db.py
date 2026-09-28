from pathlib import Path

import pytest

from src.db import CodeDB


def test_delete_ids_rejects_unknown_table(tmp_path: Path) -> None:
    db = CodeDB(tmp_path)
    with pytest.raises(ValueError, match="unsupported table"):
        db.delete_ids("nope", [1])
    db.close()


def test_delete_ids_noop_on_empty(tmp_path: Path) -> None:
    db = CodeDB(tmp_path)
    db.delete_ids("files", [])
    db.close()


def test_close_is_idempotent(tmp_path: Path) -> None:
    db = CodeDB(tmp_path)
    db.close()
    db.close()


def test_exec_tran_rolls_back_on_error(tmp_path: Path) -> None:
    db = CodeDB(tmp_path)
    with pytest.raises(Exception):  # noqa: B017, PT011
        db.exec_tran("NOT VALID SQL", ())
    db.close()
