"""Path finder: glob-style match over indexed files and directories."""

from src.db import CodeDB

_MAX_RESULTS = 100

_FILES_SQL = """
SELECT
    'file' AS row_type,
    path,
    line_count,
    symbol_count
FROM files
WHERE lower(path) GLOB lower(?)
{test_filter}
ORDER BY path
LIMIT ?
"""

_DIRS_SQL = """
SELECT
    'directory' AS row_type,
    path,
    NULL AS line_count,
    NULL AS symbol_count
FROM directories
WHERE lower(path) GLOB lower(?)
ORDER BY path
LIMIT ?
"""


def _normalize_glob(pattern: str) -> str:
    """Turn user input into a SQLite GLOB (``*``, ``?`` only; ``**`` → ``*``)."""
    raw = pattern.strip().replace("\\", "/")
    if not raw:
        return ""
    while "**" in raw:
        raw = raw.replace("**", "*")
    # Bare substring (no wildcards) → contains match.
    if "*" not in raw and "?" not in raw:
        return f"*{raw}*"
    return raw


def find_paths(
    db: CodeDB, pattern: str, limit: int = 50, *, include_tests: bool = False
) -> str:
    """
    Match indexed file and directory paths against a glob-style ``pattern``.

    Examples: ``*dialect*``, ``sqlmesh/core/*.py``, ``**/cli/main.py``.
    Does not search file contents — use ``search_symbols`` for that.

    By default skips ``is_test`` files. Pass ``include_tests=True`` to include
    them. Directories are always matched.
    """
    glob = _normalize_glob(pattern)
    if not glob:
        return "pattern is empty"

    cap = max(1, min(int(limit), _MAX_RESULTS))
    # Fetch up to cap from each table, then merge/sort/truncate.
    file_rows = list(
        db.connection.execute(
            _FILES_SQL.format(test_filter="" if include_tests else "  AND is_test = 0"),
            (glob, cap),
        )
    )
    dir_rows = list(db.connection.execute(_DIRS_SQL, (glob, cap)))
    rows = sorted(
        [*dir_rows, *file_rows],
        key=lambda r: (r["path"] or "").lower(),
    )[:cap]

    if not rows:
        return f"No indexed paths match {pattern.strip()!r} (glob {glob!r})."

    lines: list[str] = [
        "Legend: L = Lines, S = Symbols\n",
        f"Paths matching {pattern.strip()!r} — {len(rows)} result"
        + ("s" if len(rows) != 1 else ""),
        "",
    ]
    for row in rows:
        path = row["path"] or ""
        if row["row_type"] == "directory":
            lines.append(f"{path}/")
            continue
        lines_n = int(row["line_count"] or 0)
        symbols_n = int(row["symbol_count"] or 0)
        if lines_n == 0:
            lines.append(path)
        elif symbols_n == 0:
            lines.append(f"{path} ({lines_n}L)")
        else:
            lines.append(f"{path} ({lines_n}L, {symbols_n}S)")

    return "\n".join(lines).rstrip() + "\n"
