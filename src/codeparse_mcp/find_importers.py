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
WHERE i.imported_file_id = ?
   OR i.import_path = ?
ORDER BY f.path, i.line_number, i.imported_symbol
"""


def find_importers(db: CodeDB, file_path: str) -> str:
    """
    List files that import the module at ``file_path``.

    ``file_path`` is normalized to a POSIX path relative to the index root
    (e.g. ``sqlmesh/core/dialect.py``). Matching uses ``imports.imported_file_id``
    when resolved, and ``imports.import_path`` as a fallback for unresolved rows
    that still name the module's ``normalized_path``.
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
            f"No indexed file matches {path!r}. "
            f"Use the local path as stored in the index (relative to {db.root}), "
            f"e.g. via get_directory_tree or get_file_overview."
        )

    target_id = int(target["id"])
    target_path = target["path"]
    target_dotted = target["normalized_path"]

    rows = list(db.connection.execute(_IMPORTERS_SQL, (target_id, target_dotted)))
    if not rows:
        return f"No importers of {target_path} in the index."

    # Group by importer file; within a file, collapse duplicate signatures.
    by_file: OrderedDict[str, list] = OrderedDict()
    for row in rows:
        by_file.setdefault(row["importer_path"], []).append(row)

    total_files = len(by_file)
    shown_files = list(by_file.items())[:_MAX_IMPORTER_FILES]

    lines_out: list[str] = [
        "Legend: L = Lines, S = Symbols\n",
        f"Importers of {target_path} — {total_files} files",
        "",
    ]

    for importer_path, file_rows in shown_files:
        seen_sigs: set[str] = set()
        symbols: list[str] = []
        seen_symbols: set[str] = set()
        stmt_lines: list[str] = []
        for row in file_rows:
            sig = (row["signature"] or "").strip()
            line_n = int(row["line_number"])
            if sig and sig not in seen_sigs:
                seen_sigs.add(sig)
                stmt_lines.append(f"  {sig} ({line_n}L)")
            elif not sig:
                key = f"{line_n}:{row['imported_symbol']}"
                if key not in seen_sigs:
                    seen_sigs.add(key)
                    sym = row["imported_symbol"] or "(module)"
                    stmt_lines.append(f"  {sym} ({line_n}L)")
            sym = (row["imported_symbol"] or "").strip()
            if sym and sym not in seen_symbols:
                seen_symbols.add(sym)
                symbols.append(sym)
        # Match directory_tree file stats: name (NS) / (NL, NS).
        if symbols:
            lines_out.append(f"{importer_path} ({len(symbols)}S)")
        else:
            lines_out.append(importer_path)
        lines_out.extend(stmt_lines)
        lines_out.append("")

    if total_files > _MAX_IMPORTER_FILES:
        omitted = total_files - _MAX_IMPORTER_FILES
        lines_out.append(f"...[{omitted} more importer files truncated]")

    return "\n".join(lines_out).rstrip() + "\n"
