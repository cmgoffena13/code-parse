import sqlite3
from collections import OrderedDict

from src.codeparse_mcp.format_utils import file_label, line_span
from src.db import CodeDB

_SYMBOL_SEARCH_SQL = """
SELECT
    s.qualified_name,
    s.line_start,
    s.line_end,
    f.path AS path,
    f.line_count AS file_line_count,
    f.symbol_count AS file_symbol_count,
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
    """Turn free text into an OR of prefix terms (e.g. ``auth login`` → ``auth* OR login*``).

    Tokens are always OR'd. Do not treat ``AND``/``OR``/``NOT`` in the input as
    FTS operators — they become ordinary terms.
    """
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

    Query is space-separated phrases/terms, OR'd with prefix matching. Returns
    ranked hits grouped by file (path + line/symbol counts; each hit has
    line span + ``qualified_name``, ordered by ``line_start``) for
    ``get_symbol_context``. By default skips ``is_test`` files; pass
    ``include_tests=True`` to include them.
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
        "Legend: L = Line / Lines, S = Symbols\n",
        f'Search results for "{stripped}" ({len(rows)} matches)',
        "",
    ]
    for path_index, (path, sym_rows) in enumerate(by_path.items()):
        if path_index > 0:
            lines.append("")
        lines.append(
            file_label(
                path,
                int(sym_rows[0]["file_line_count"] or 0),
                int(sym_rows[0]["file_symbol_count"] or 0),
            )
        )
        ordered = sorted(
            sym_rows,
            key=lambda r: (
                int(r["line_start"] or 0),
                int(r["line_end"] or 0),
                (r["qualified_name"] or ""),
            ),
        )
        for row in ordered:
            qn = (row["qualified_name"] or "").strip()
            if not qn:
                continue
            loc = line_span(int(row["line_start"] or 0), int(row["line_end"] or 0))
            lines.append(f"  • {loc}  {qn}")

    return "\n".join(lines).rstrip() + "\n"
