import sqlite3
from collections import OrderedDict

from src.db import CodeDB

_SYMBOL_SEARCH_SQL = """
SELECT
    s.qualified_name,
    s.line_count,
    f.path AS path,
    f.line_count AS file_line_count,
    bm25(symbols_fts) AS rank
FROM symbols_fts
INNER JOIN symbols AS s
    ON s.id = symbols_fts.rowid
INNER JOIN files AS f
    ON f.id = s.file_id
WHERE symbols_fts MATCH ?
{test_filter}
ORDER BY rank
LIMIT ?
"""


def build_fts_query(user_input: str) -> str:
    """Turn free text into an OR-based prefix query for FTS5 (e.g. ``auth login`` → ``auth* OR login*``)."""
    terms = user_input.strip().split()
    if not terms:
        return ""
    return " OR ".join(f"{term}*" for term in terms)


def search_symbols(
    db: CodeDB,
    query: str,
    limit: int = 10,
    *,
    include_tests: bool = False,
) -> str:
    """
    Search indexed symbols via ``symbols_fts`` (qualified_name, signature,
    docstring). Repo-wide only — use ``get_file_overview`` to map one file.

    Returns ranked hits grouped by file. Each file header includes that file's
    line count, and each hit includes ``qualified_name`` and line count for
    follow-up with ``get_symbol_context``. By default skips symbols in
    ``is_test`` files; pass ``include_tests=True`` to search those too.
    """
    stripped = query.strip()
    if not stripped:
        return "No search text given; pass a non-empty query."

    fts_query = build_fts_query(stripped)
    if not fts_query:
        return "No search text given; pass a non-empty query."

    try:
        rows = db.connection.execute(
            _SYMBOL_SEARCH_SQL.format(
                test_filter="" if include_tests else "  AND f.is_test = 0",
            ),
            (fts_query, limit),
        ).fetchall()
    except sqlite3.OperationalError as e:
        return f"Search failed for {query!r} ({fts_query!r}): {e}"

    by_path: OrderedDict[str, list] = OrderedDict()
    for row in rows:
        path = row["path"] or ""
        by_path.setdefault(path, []).append(row)

    lines: list[str] = [
        "Legend: L = Lines\n",
        f'Search results for "{stripped}" ({len(rows)} matches)',
        "",
    ]
    for path_index, (path, sym_rows) in enumerate(by_path.items()):
        if path_index > 0:
            lines.append("")
        header = path or "(unknown path)"
        file_n = int(sym_rows[0]["file_line_count"] or 0)
        if file_n:
            header = f"{header} ({file_n}L)"
        lines.append(header)
        for row in sym_rows:
            qn = (row["qualified_name"] or "").strip()
            if not qn:
                continue
            n = int(row["line_count"] or 0)
            lines.append(f"  • {qn} ({n}L)")

    return "\n".join(lines).rstrip() + "\n"
