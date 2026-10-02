"""Repo map: largest directories and where the program starts."""

import re
import tomllib
from pathlib import Path

from src.codeparse_mcp.format_utils import file_label
from src.db import CodeDB

_TOP_DIRECTORIES = 10

_DIRECTORIES_SQL = """
SELECT
    COALESCE(d.path, '.') AS path,
    COUNT(f.id) AS file_count,
    COALESCE(SUM(f.line_count), 0) AS line_count,
    COALESCE(SUM(f.symbol_count), 0) AS symbol_count
FROM files AS f
LEFT JOIN directories AS d
    ON d.id = f.directory_id
WHERE f.is_test = 0
GROUP BY COALESCE(d.path, '.')
HAVING COALESCE(SUM(f.symbol_count), 0) > 0
ORDER BY symbol_count DESC, path
LIMIT ?
"""

_PYTHON_FILES_SQL = """
SELECT path, name, normalized_path, line_count, symbol_count
FROM files
WHERE is_test = 0
    AND (language = 'python' OR name LIKE '%.py')
ORDER BY path
"""

_MAIN_GUARD = re.compile(r"""(?m)^[ \t]*if[ \t]+__name__[ \t]*==[ \t]*(['"])__main__\1[ \t]*:""")


def _script_targets(root: Path) -> tuple[list[tuple[str, str]], str | None]:
    """Return ``(command, qualified_name)`` pairs, plus a parse error if any."""
    path = root / "pyproject.toml"
    if not path.is_file():
        return [], None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        return [], f"pyproject.toml could not be parsed: {exc}"
    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return [], None
    targets: list[tuple[str, str]] = []
    for name in sorted(scripts):
        target = scripts[name]
        if not isinstance(target, str) or not target.strip():
            continue
        targets.append((name, target.strip().replace(":", ".", 1)))
    return targets, None


def _entry_point_lines(db: CodeDB) -> list[str]:
    """One line per file. Scripts, then ``app.py`` / ``main.py``, then ``__main__``."""
    by_module: dict[str, str] = {}
    file_stats: dict[str, tuple[int, int]] = {}
    named: set[str] = set()
    guards: set[str] = set()
    for row in db.connection.execute(_PYTHON_FILES_SQL):
        path = row["path"]
        file_stats[path] = (
            int(row["line_count"] or 0),
            int(row["symbol_count"] or 0),
        )
        module = (row["normalized_path"] or "").lower()
        if module:
            by_module[module] = path
        if row["name"] in ("app.py", "main.py"):
            named.add(path)
        file_path = db.root / path
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _MAIN_GUARD.search(text):
            guards.add(path)

    def _bullet(path: str) -> str:
        line_count, symbol_count = file_stats.get(path, (0, 0))
        return f"  • {file_label(path, line_count, symbol_count)}"

    scripts, _error = _script_targets(db.root)
    lines: list[str] = []
    claimed: set[str] = set()
    for _command, qualified in scripts:
        module = qualified.rsplit(".", 1)[0] if "." in qualified else qualified
        path = by_module.get(module.lower())
        if path is None or path in claimed:
            continue
        claimed.add(path)
        lines.append(_bullet(path))

    for path in sorted(named - claimed):
        lines.append(_bullet(path))
        claimed.add(path)

    for path in sorted(guards - claimed):
        lines.append(_bullet(path))

    return lines or ["No entry points."]


def get_project_overview(db: CodeDB) -> str:
    """
    Top directories by symbol count, plus entry points from ``pyproject.toml``
    scripts, ``app.py`` / ``main.py``, and ``if __name__ == "__main__"``.

    Counts use files that sit directly in each directory. Test files are skipped.
    """
    directories = list(db.connection.execute(_DIRECTORIES_SQL, (_TOP_DIRECTORIES,)).fetchall())
    entry_points = _entry_point_lines(db)

    lines = [
        f"Project: {db.root.name}",
        "",
        "Legend: L = Lines, S = Symbols, F = Files",
        "",
        "Directories - Top 10",
        "",
    ]
    if directories:
        for row in directories:
            symbols = int(row["symbol_count"])
            line_count = int(row["line_count"])
            files = int(row["file_count"])
            lines.append(f"  • {row['path']} ({line_count}L, {symbols}S, {files}F)")
    else:
        lines.append("No symbols.")

    lines.extend(["", "Entrypoints", ""])
    lines.extend(entry_points)

    return "\n".join(lines).rstrip() + "\n"
