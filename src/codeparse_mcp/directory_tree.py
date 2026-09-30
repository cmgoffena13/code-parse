from collections import defaultdict

from src.codeparse_mcp.format_utils import file_label
from src.codeparse_mcp.paths import normalize_repo_file_path
from src.db import CodeDB

_TREE_SQL = """
SELECT
    'directory' AS row_type,
    id,
    parent_id AS parent_id,
    name,
    NULL AS line_count,
    NULL AS symbol_count
FROM directories
UNION ALL
SELECT
    'file' AS row_type,
    id,
    directory_id AS parent_id,
    name,
    line_count,
    symbol_count
FROM files
"""


def _lines_under_parent(children_by_parent_id, parent_key, branch_prefix):
    lines = []
    siblings = children_by_parent_id.get(parent_key, ())
    last_index = len(siblings) - 1
    for index, (is_directory, row) in enumerate(siblings):
        is_last_child = index == last_index
        connector = "└── " if is_last_child else "├── "
        if is_directory:
            display_name = row["name"] + "/"
        else:
            display_name = file_label(
                row["name"],
                row["line_count"] or 0,
                row["symbol_count"] if row["symbol_count"] is not None else 0,
            )
        lines.append(f"{branch_prefix}{connector}{display_name}")
        if is_directory:
            continuation = "    " if is_last_child else "│   "
            next_prefix = branch_prefix + continuation
            lines.extend(
                _lines_under_parent(children_by_parent_id, row["id"], next_prefix)
            )
    return lines


def get_directory_tree(db: CodeDB, path: str | None = None) -> str:
    """
    Return the directory/file tree with line and symbol counts.

    Optional ``path`` scopes to one directory tree (exact path).
    """
    children_by_parent_id = defaultdict(list)
    for row in db.connection.execute(_TREE_SQL):
        is_directory = row["row_type"] == "directory"
        children_by_parent_id[row["parent_id"]].append((is_directory, row))
    for sibling_list in children_by_parent_id.values():
        sibling_list.sort(
            key=lambda item: (not item[0], item[1]["name"].lower()),
        )

    root_key = None
    root_label = "."
    if path and path.strip():
        try:
            scoped = normalize_repo_file_path(path, db.root).rstrip("/")
        except ValueError as exc:
            return str(exc)
        if scoped not in ("", "."):
            dir_row = db.connection.execute(
                "SELECT id, path FROM directories WHERE path = ?",
                (scoped,),
            ).fetchone()
            if dir_row is None:
                return (
                    f"No directory matches {scoped!r}. "
                    f"Use a directory path from ``glob`` (not a file)."
                )
            root_key = dir_row["id"]
            root_label = f"{dir_row['path']}/"

    body_lines = _lines_under_parent(children_by_parent_id, root_key, "")
    if not body_lines:
        return root_label.rstrip("/") or "."
    return (
        "Legend: L = Lines, S = Symbols\n\n" + root_label + "\n" + "\n".join(body_lines)
    )
