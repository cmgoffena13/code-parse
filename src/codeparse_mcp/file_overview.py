from collections import defaultdict

from src.codeparse_mcp.paths import normalize_repo_file_path
from src.db import CodeDB

_SYMBOLS_SQL = """
SELECT
    id,
    parent_id,
    kind,
    qualified_name,
    name,
    line_start,
    line_end,
    line_count
FROM symbols
WHERE file_id = ?
ORDER BY line_start, line_end, qualified_name
"""

_IMPORTS_SQL = """
SELECT
    line_number,
    signature
FROM imports
WHERE file_id = ?
ORDER BY line_number
"""


def _symbol_label(row) -> str:
    qn = (row["qualified_name"] or row["name"] or "").strip()
    n = int(row["line_count"] or 0)
    kind = row["kind"] or ""
    return f"{kind}  {qn} ({n}L)"


def _symbol_branch_lines(
    children_by_parent_id: dict[int | None, list],
    parent_id: int | None,
    branch_prefix: str,
) -> list[str]:
    lines: list[str] = []
    siblings = children_by_parent_id.get(parent_id, ())
    last_i = len(siblings) - 1
    for index, row in enumerate(siblings):
        is_last = index == last_i
        connector = "└─ " if is_last else "├─ "
        lines.append(f"{branch_prefix}{connector}{_symbol_label(row)}")
        continuation = "   " if is_last else "│  "
        lines.extend(
            _symbol_branch_lines(
                children_by_parent_id, row["id"], branch_prefix + continuation
            )
        )
    return lines


def get_file_overview(db: CodeDB, file_path: str) -> str:
    """
    Return imports and a nested symbol tree for one file.

    Each symbol line uses ``qualified_name`` and a line-count ``(NL)`` so
    callers can pass the name to ``get_symbol_context``. ``file_path`` is
    normalized to a POSIX path relative to the index root (e.g. ``pkg/mod.py``).
    """
    try:
        path = normalize_repo_file_path(file_path, db.root)
    except ValueError as exc:
        return str(exc)

    file_row = db.connection.execute(
        "SELECT id, path, language, line_count FROM files WHERE path = ?",
        (path,),
    ).fetchone()
    if file_row is None:
        return (
            f"No indexed file matches {path!r}. "
            f"Use the local path as stored in the index (relative to {db.root})."
        )

    file_id = file_row["id"]
    imp_rows = list(db.connection.execute(_IMPORTS_SQL, (file_id,)))
    sym_rows = list(db.connection.execute(_SYMBOLS_SQL, (file_id,)))

    lines_out: list[str] = [
        "Legend: L = Lines\n",
        f"File: {file_row['path']}",
        f"Language: {file_row['language'] or '—'}",
        f"Lines: {file_row['line_count']}",
        "",
        f"## Imports ({len(imp_rows)})",
    ]
    if not imp_rows:
        lines_out.append("_(none)_")
    else:
        # One DB row per imported name from `from m import a, b` repeats the same
        # statement `signature`; show each distinct signature once.
        seen_signatures: set[str] = set()
        for row in imp_rows:
            sig = (row["signature"] or "").strip()
            if sig:
                if sig in seen_signatures:
                    continue
                seen_signatures.add(sig)
                lines_out.append(sig)
            else:
                lines_out.append("—")

    lines_out.extend(["", f"## Symbols ({len(sym_rows)})"])

    if not sym_rows:
        lines_out.append("_(none)_")
    else:
        ids_in_file = {r["id"] for r in sym_rows}

        def effective_parent_id(row) -> int | None:
            pid = row["parent_id"]
            if pid is None:
                return None
            if pid not in ids_in_file:
                return None
            return pid

        children_by_parent_id: dict[int | None, list] = defaultdict(list)
        for row in sym_rows:
            children_by_parent_id[effective_parent_id(row)].append(row)
        for bucket in children_by_parent_id.values():
            bucket.sort(
                key=lambda r: (r["line_start"], r["line_end"], r["qualified_name"])
            )

        roots = children_by_parent_id.get(None, ())
        for root_index, row in enumerate(roots):
            if root_index > 0:
                lines_out.append("")
            lines_out.append(_symbol_label(row))
            lines_out.extend(_symbol_branch_lines(children_by_parent_id, row["id"], ""))

    return "\n".join(lines_out) + "\n"
