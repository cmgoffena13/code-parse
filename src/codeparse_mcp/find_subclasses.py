"""Classes that directly inherit from a given class."""

from src.db import CodeDB

_MAX_SUBCLASSES = 100

_SUBCLASSES_SQL = """
SELECT
    s.qualified_name,
    s.line_start,
    f.path AS file_path
FROM symbol_bases AS sb
INNER JOIN symbols AS s
    ON s.id = sb.symbol_id
INNER JOIN files AS f
    ON f.id = s.file_id
WHERE sb.base_qualified_name = ?
{test_filter}
ORDER BY f.path, s.line_start, s.qualified_name
"""


def find_subclasses(
    db: CodeDB, qualified_name: str, *, include_tests: bool = False
) -> str:
    """
    List classes whose base list includes ``qualified_name``.

    One hop only: ``class Grand(Child)`` is not listed for ``Parent``. Test
    files are skipped unless ``include_tests`` is true.
    """
    key = qualified_name.strip()
    if not key:
        return "No symbol name given; pass a non-empty qualified_name."

    rows = list(
        db.connection.execute(
            _SUBCLASSES_SQL.format(
                test_filter="" if include_tests else "    AND f.is_test = 0"
            ),
            (key,),
        )
    )
    if not rows:
        return f"No subclasses of {key} found."

    total = len(rows)
    shown = rows[:_MAX_SUBCLASSES]
    label = "class" if total == 1 else "classes"
    lines_out = [
        "Legend: • path:line - qualified_name\n",
        f"Subclasses of {key} — {total} {label}",
        "",
    ]
    for row in shown:
        lines_out.append(
            f"  • {row['file_path']}:{int(row['line_start'])} - {row['qualified_name']}"
        )

    if total > _MAX_SUBCLASSES:
        omitted = total - _MAX_SUBCLASSES
        lines_out.append("")
        lines_out.append(f"...[{omitted} more subclasses truncated]")

    return "\n".join(lines_out).rstrip() + "\n"
