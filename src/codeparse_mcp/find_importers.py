"""Reverse-import lookup: which files import a given module."""

from collections import OrderedDict

from src.db import CodeDB

_MAX_IMPORTER_FILES = 100

_RESOLVE_FILE_SQL = """
SELECT id, path, normalized_path
FROM files
WHERE path = ? OR normalized_path = ?
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


def _path_and_dotted(module_or_path: str) -> tuple[str, str]:
    """Map user input to a file path candidate and a dotted module candidate."""
    raw = module_or_path.strip().replace("\\", "/")
    if raw.endswith(".py"):
        path = raw
        dotted = raw[: -len(".py")].replace("/", ".")
    elif "/" in raw:
        path = f"{raw}.py"
        dotted = raw.replace("/", ".")
    else:
        dotted = raw
        path = raw.replace(".", "/") + ".py"
    return path, dotted


def find_importers(db: CodeDB, module_or_path: str) -> str:
    """
    List files that import the given module.

    ``module_or_path`` may be a repo-relative path (``sqlmesh/core/dialect.py``)
    or a dotted module (``sqlmesh.core.dialect``). Matching uses
    ``imports.imported_file_id`` when resolved, and ``imports.import_path`` as
    a fallback for unresolved rows that still name the module.
    """
    stripped = module_or_path.strip()
    if not stripped:
        return "No module or path given; pass a non-empty module_or_path."

    path, dotted = _path_and_dotted(stripped)
    target = db.connection.execute(_RESOLVE_FILE_SQL, (path, dotted)).fetchone()
    if target is None:
        return (
            f"No indexed file matches {stripped!r} "
            f"(tried path {path!r} and module {dotted!r}). "
            f"Use a path relative to {db.root} or its dotted module form."
        )

    target_id = int(target["id"])
    target_path = target["path"]
    target_dotted = target["normalized_path"]

    rows = list(db.connection.execute(_IMPORTERS_SQL, (target_id, target_dotted)))
    if not rows:
        return f"No importers of {target_path} ({target_dotted}) in the index."

    # Group by importer file; within a file, collapse duplicate signatures.
    by_file: OrderedDict[str, list] = OrderedDict()
    for row in rows:
        by_file.setdefault(row["importer_path"], []).append(row)

    total_files = len(by_file)
    shown_files = list(by_file.items())[:_MAX_IMPORTER_FILES]

    lines_out: list[str] = [
        f"Importers of {target_path} ({target_dotted}) — {total_files} files",
        "",
    ]

    for importer_path, file_rows in shown_files:
        lines_out.append(importer_path)
        seen_sigs: set[str] = set()
        symbols: list[str] = []
        seen_symbols: set[str] = set()
        for row in file_rows:
            sig = (row["signature"] or "").strip()
            if sig and sig not in seen_sigs:
                seen_sigs.add(sig)
                lines_out.append(f"  L{row['line_number']}: {sig}")
            elif not sig:
                key = f"{row['line_number']}:{row['imported_symbol']}"
                if key not in seen_sigs:
                    seen_sigs.add(key)
                    sym = row["imported_symbol"] or "(module)"
                    lines_out.append(f"  L{row['line_number']}: {sym}")
            sym = (row["imported_symbol"] or "").strip()
            if sym and sym not in seen_symbols:
                seen_symbols.add(sym)
                symbols.append(sym)
        if symbols:
            lines_out.append(f"  symbols: {', '.join(symbols)}")
        lines_out.append("")

    if total_files > _MAX_IMPORTER_FILES:
        omitted = total_files - _MAX_IMPORTER_FILES
        lines_out.append(f"...[{omitted} more importer files truncated]")

    return "\n".join(lines_out).rstrip() + "\n"
