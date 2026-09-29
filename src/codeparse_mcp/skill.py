from pathlib import Path

SKILL_INSTRUCTIONS = """\
---
name: codeparse
description: Use the codeparse MCP Server effectively.
allowed-tools: get_directory_tree get_file_overview search_symbols get_symbol_context find_importers
---

## Identifiers

Symbols are keyed by **qualified_name** (module-prefixed for Python), e.g.
`src.db.CodeDB` or `src.processor.CodeProcessor.process` — not the bare name
(`CodeDB`, `process`). Always copy `qualified_name` from tool output into
`get_symbol_context`. Never invent or shorten it.

## Pick the narrowest tool

Do **not** start every question with `get_directory_tree`. That tool returns the
**entire** repo and is expensive on large codebases. Prefer:

| Question type | Tool |
| --- | --- |
| Known file / package API (`__init__.py`, public exports) | `get_file_overview` on that path |
| "Where is X defined?" / keyword hunt | `search_symbols` → `get_symbol_context` |
| "Who calls / references symbol S?" | `search_symbols` → `get_symbol_context` |
| "Who imports module M?" | `find_importers` (repo-relative path) |
| Lost in an unfamiliar repo (no path hint) | `get_directory_tree` **once**, then stop |

## Workflow details

### search_symbols → get_symbol_context
- Prefer specific terms from the request.
- Copy the exact **`qualified_name`** from hits into `get_symbol_context`.
- Use this for definitions, callers, and reference traces.

### get_file_overview
- One file's imports + symbol tree (each node has `qualified_name`).
- Best for package surfaces: e.g. `sqlmesh/core/model/__init__.py`, not the
  whole tree plus every sibling module.
- `file_path` is relative to the index root with POSIX slashes.

### find_importers
- Fan-in for a module file. Pass the same path style as `get_file_overview`
  (`pkg/mod.py`).
- Do not discover importers by sampling `get_file_overview` across files.

### get_directory_tree
- Full-repo layout with line/symbol counts.
- Only when you truly lack a map and the user did not name a path.
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
