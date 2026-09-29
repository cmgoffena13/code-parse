from pathlib import Path

SKILL_INSTRUCTIONS = """\
---
name: codeparse
description: Use the codeparse MCP Server effectively.
allowed-tools: get_directory_tree find_paths get_file_overview search_symbols get_symbol_context find_importers
---

## Identifiers

Symbols are keyed by **qualified_name** (module-prefixed for Python), e.g.
`src.db.CodeDB` or `src.processor.CodeProcessor.process` — not the bare name
(`CodeDB`, `process`). Always copy `qualified_name` from tool output into
`get_symbol_context`. Never invent or shorten it.

## Pick the narrowest tool

| Question type | Tool |
| --- | --- |
| Known file / package API (`__init__.py`, public exports) | `get_file_overview` on that path |
| Filename / path hunt (`*dialect*`, `**/cli/*.py`) | `find_paths` |
| "Where is X defined?" / keyword hunt | `search_symbols` → `get_symbol_context` |
| "Who calls / references symbol S?" | `search_symbols` → `get_symbol_context` |
| "Who imports module M?" | `find_importers` (file path) |
| Lost in an unfamiliar repo (no path hint) | `get_directory_tree` **once**, then stop |
| Local layout under a known directory | `find_paths` → `get_directory_tree(path=…)` |

## Workflow details

### find_paths
- Glob-style match over indexed paths (not file contents).
- Use before ``search_symbols`` when the clue is a filename or directory.
- Defaults to skipping ``is_test`` files; set ``include_tests`` when you need them.

### search_symbols → get_symbol_context
- Prefer specific terms from the request.
- Copy the exact **`qualified_name`** from hits into `get_symbol_context`.
- Use this for definitions, callers, and reference traces.
- ``search_symbols`` is repo-wide. To map one known file, use ``get_file_overview``.
- ``search_symbols`` defaults to skipping ``is_test`` files; set ``include_tests``
  when you need them. ``get_symbol_context`` definitions omit references unless
  ``include_references`` is set.

### get_file_overview
- One file's imports + symbol tree (each node has `qualified_name`).
- Best for package surfaces: e.g. `sqlmesh/core/model/__init__.py`, not the
  whole tree plus every sibling module.

### find_importers
- Fan-in for a module file. 
- Use to discover importers instead of sampling `get_file_overview` across files.
- Defaults to skipping importer files marked ``is_test``; only set
  ``include_tests`` when you need them.

### get_directory_tree
- Layout with line/symbol counts. Omit ``path`` only when you lack any map.
- When ``find_paths`` returns a directory, pass that exact path to scope the
  tree to that branch — never dump the full repo after you already have a path.
- Never call it repeatedly in one task.

## Rules
- Never guess a `qualified_name`. Take it only from tool output.
- Prefer one targeted call over many broad ones.
- Cite file paths and line numbers in every response.
"""


def generate_skill(root: Path | None = None) -> Path:
    base = (root or Path.cwd()).resolve()
    output_path = base / ".claude" / "skills" / "codeparse" / "SKILL.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SKILL_INSTRUCTIONS, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(generate_skill())
