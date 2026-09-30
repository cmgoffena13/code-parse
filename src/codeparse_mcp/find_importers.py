"""Reverse-import lookup: which files import a given module."""

from collections import OrderedDict

from src.codeparse_mcp.paths import normalize_repo_file_path
from src.db import CodeDB

_MAX_IMPORTER_FILES = 100

_RESOLVE_FILE_SQL = """
SELECT id, path, normalized_path
FROM files
WHERE path = ?
LIMIT 1
"""

_IMPORTERS_SQL = """
SELECT
    f.path AS importer_path,
    i.line_number,
    i.imported_symbol,
    i.signature,
    i.import_path
FROM imports AS i
INNER JOIN files AS f
    ON f.id = i.file_id
WHERE (i.imported_file_id = ? OR i.import_path = ?)
{test_filter}
ORDER BY f.path, i.line_number, i.imported_symbol
"""


def find_importers(db: CodeDB, file_path: str, *, include_tests: bool = False) -> str:
    """
    List files that import the module at ``file_path``.

    ``file_path`` is normalized to a POSIX path relative to the workspace root
    (e.g. ``sqlmesh/core/dialect.py``). Matching uses ``imports.imported_file_id``
    when resolved, and ``imports.import_path`` as a fallback for unresolved rows
    that still name the module's ``normalized_path``.

    By default skips importer files marked ``is_test`` (path rules: ``tests/``,
    ``test_*.py``, etc.). Pass ``include_tests=True`` to include them.
    """
    try:
        path = normalize_repo_file_path(file_path, db.root)
    except ValueError as exc:
        return str(exc)

    target = db.connection.execute(_RESOLVE_FILE_SQL, (path,)).fetchone()
    if target is None and not path.endswith(".py"):
        target = db.connection.execute(_RESOLVE_FILE_SQL, (f"{path}.py",)).fetchone()
    if target is None:
        return (
            f"No file matches {path!r}. "
            f"Use a repo-relative path (relative to {db.root}), "
            f"e.g. via get_directory_tree or get_file_overview."
        )

    target_id = int(target["id"])
    target_path = target["path"]
    target_dotted = target["normalized_path"]

    rows = list(
        db.connection.execute(
            _IMPORTERS_SQL.format(
                test_filter="" if include_tests else "  AND f.is_test = 0"
            ),
            (target_id, target_dotted),
        )
    )
    if not rows:
        return f"No importers of {target_path} were found."

    # Group by importer file, then by line, collecting imported names.
    by_file: OrderedDict[str, OrderedDict[int, list[str]]] = OrderedDict()
    for row in rows:
        importer_path = row["importer_path"]
        line_n = int(row["line_number"])
        sym = (row["imported_symbol"] or "").strip() or "(module)"
        lines = by_file.setdefault(importer_path, OrderedDict())
        names = lines.setdefault(line_n, [])
        if sym not in names:
            names.append(sym)

    total_files = len(by_file)
    shown_files = list(by_file.items())[:_MAX_IMPORTER_FILES]

    lines_out: list[str] = [
        "Legend: • path:line - imported symbols\n",
        f"Importers of {target_path} — {total_files} files",
        "",
    ]
    for importer_path, by_line in shown_files:
        for line_n, names in by_line.items():
            lines_out.append(f"  • {importer_path}:{line_n} - {', '.join(names)}")

    if total_files > _MAX_IMPORTER_FILES:
        omitted = total_files - _MAX_IMPORTER_FILES
        lines_out.append("")
        lines_out.append(f"...[{omitted} more importer files truncated]")

    return "\n".join(lines_out).rstrip() + "\n"
