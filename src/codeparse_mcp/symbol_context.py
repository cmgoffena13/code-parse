from collections import OrderedDict, defaultdict

from src.codeparse_mcp.format_utils import lines_range
from src.db import CodeDB

_REFERENCE_FETCH_LIMIT = 50

_SYMBOL_ROW_SQL = """
SELECT
    s.line_start,
    s.line_end,
    s.qualified_name,
    f.path AS file_path,
    s.kind,
    f.language AS file_language
FROM symbols AS s
INNER JOIN files AS f
    ON f.id = s.file_id
WHERE s.qualified_name = ?
"""

_REFERENCES_SQL = """
SELECT
    f.path AS source_path,
    sr.source_line,
    sr.ref_kind
FROM symbol_references AS sr
INNER JOIN files AS f
    ON f.id = sr.source_file_id
WHERE sr.ref_symbol_qualified_name = ?
ORDER BY sr.ref_kind, f.path, sr.source_line
LIMIT ?
"""

_REF_KIND_SECTIONS: tuple[tuple[str, str], ...] = (
    ("call", "## Calls"),
    ("access", "## Access"),
    ("type_annotation", "## Type Annotations"),
)


def _definition_gutter_width(line_start: int, line_count: int) -> int:
    if line_count <= 0:
        return len(str(line_start))
    return len(str(line_start + line_count - 1))


def _reference_section_lines(heading: str, items: list) -> list[str]:
    """Group reference rows by file under ``heading`` with ``L{n}`` bullets."""
    by_file: OrderedDict[str, list[int]] = OrderedDict()
    for r in items:
        path = r["source_path"]
        by_file.setdefault(path, []).append(int(r["source_line"]))

    lines_out = [
        "",
        f"{heading} ({len(items)})",
        "",
    ]
    for path_index, (path, line_nums) in enumerate(by_file.items()):
        if path_index > 0:
            lines_out.append("")
        lines_out.append(path)
        for line_n in line_nums:
            lines_out.append(f"  • L{line_n}")
    return lines_out


def get_symbol_context(
    db: CodeDB,
    qualified_name: str,
    *,
    include_references: bool = False,
) -> str:
    """
    Return symbol metadata and source for the indexed span. With
    ``include_references=True``, also append reference subsections grouped by
    ``ref_kind`` then file (only kinds with at least one row are shown).

    ``qualified_name`` must equal ``symbols.qualified_name`` (module-prefixed for
    Python). Bare names do not match.
    """
    key = qualified_name.strip()
    if not key:
        return "No symbol name given; pass a non-empty qualified_name."

    row = db.connection.execute(_SYMBOL_ROW_SQL, (key,)).fetchone()
    if row is None:
        return f"No symbol with qualified_name {key!r} in the index."

    path = row["file_path"]
    line_start = int(row["line_start"])
    line_end = int(row["line_end"])
    lang = row["file_language"] or "—"

    abs_path = db.root / path
    body_lines: list[str] = []
    try:
        raw_lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line_start < 1:
            body_lines.append("    (invalid line_start in index)")
        else:
            chunk = raw_lines[line_start - 1 : line_end]
            if not chunk:
                body_lines.append("    (no lines in range)")
            else:
                gutter = _definition_gutter_width(line_start, len(chunk))
                for index, ln in enumerate(chunk):
                    lineno = line_start + index
                    body_lines.append(f"  L{lineno:<{gutter}}  {ln}")
    except OSError as e:
        body_lines.append(f"    (could not read source file: {e})")

    lines: list[str] = [
        "Legend: L = Line\n",
        f"Symbol: {key}",
        f"Kind: {row['kind']}",
        f"File: {path}",
        f"Language: {lang}",
        f"Lines: {lines_range(line_start, line_end)}",
        "",
        "## Code Definition",
        "",
    ]
    lines.extend(body_lines)

    if include_references:
        ref_rows = db.connection.execute(
            _REFERENCES_SQL,
            (key, _REFERENCE_FETCH_LIMIT),
        ).fetchall()
        by_kind: defaultdict[str, list] = defaultdict(list)
        for r in ref_rows:
            by_kind[r["ref_kind"]].append(r)

        covered = {k for k, _ in _REF_KIND_SECTIONS}
        for kind, heading in _REF_KIND_SECTIONS:
            items = by_kind.get(kind, [])
            if not items:
                continue
            lines.extend(_reference_section_lines(heading, items))

        for kind in sorted(by_kind.keys()):
            if kind in covered:
                continue
            items = by_kind[kind]
            if not items:
                continue
            title = kind.replace("_", " ").title()
            lines.extend(_reference_section_lines(f"## {title}", items))

    return "\n".join(lines) + "\n"
