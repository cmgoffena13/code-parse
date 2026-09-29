import sqlite3
from collections import OrderedDict

from src.codeparse_mcp.paths import normalize_repo_file_path
from src.db import CodeDB

_SYMBOL_SEARCH_SQL = """
SELECT
    s.qualified_name,
    s.line_count,
    f.path AS path,
    bm25(symbols_fts) AS rank
FROM symbols_fts
INNER JOIN symbols AS s
    ON s.id = symbols_fts.rowid
INNER JOIN files AS f
    ON f.id = s.file_id
WHERE symbols_fts MATCH ?
{path_filter}
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
    file_path: str | None = None,
    include_tests: bool = False,
) -> str:
    """
    Search indexed symbols via ``symbols_fts`` (qualified_name, signature,
    docstring). Returns ranked hits grouped by file with ``qualified_name``
    and line count for follow-up with ``get_symbol_context``.

    Optional ``file_path`` scopes to one indexed file (exact path, same
    normalization as ``get_file_overview``). By default skips symbols in
    ``is_test`` files; pass ``include_tests=True`` to search those too.
    """
    stripped = query.strip()
    if not stripped:
        return "No search text given; pass a non-empty query."

    fts_query = build_fts_query(stripped)
    if not fts_query:
        return "No search text given; pass a non-empty query."

    params: list[object] = [fts_query]
    path_filter = ""
    scoped_path: str | None = None
    if file_path and file_path.strip():
        try:
            scoped_path = normalize_repo_file_path(file_path, db.root)
        except ValueError as exc:
            return str(exc)
        path_filter = "  AND f.path = ?"
        params.append(scoped_path)
    params.append(limit)

    try:
        rows = db.connection.execute(
            _SYMBOL_SEARCH_SQL.format(
                path_filter=path_filter,
                test_filter="" if include_tests else "  AND f.is_test = 0",
            ),
            params,
        ).fetchall()
    except sqlite3.OperationalError as e:
        return f"Search failed for {query!r} ({fts_query!r}): {e}"

    by_path: OrderedDict[str, list] = OrderedDict()
    for row in rows:
        path = row["path"] or ""
        by_path.setdefault(path, []).append(row)

    scope = f' in "{scoped_path}"' if scoped_path else ""
    lines: list[str] = [
        "Legend: L = Lines\n",
        f'Search results for "{stripped}"{scope} ({len(rows)} matches)',
        "",
    ]
    for path_index, (path, sym_rows) in enumerate(by_path.items()):
        if path_index > 0:
            lines.append("")
        lines.append(path or "(unknown path)")
        for row in sym_rows:
            qn = (row["qualified_name"] or "").strip()
            if not qn:
                continue
            n = int(row["line_count"] or 0)
            lines.append(f"  • {qn} ({n}L)")

    return "\n".join(lines).rstrip() + "\n"
