from pathlib import Path

_SKILL_INSTRUCTIONS = """\
---
name: Code-Parse
description: Use the Code-Parse MCP Server effectively.
allowed-tools: get_directory_tree get_file_overview search_symbols get_symbol_context
---

## Identifiers

Symbols are keyed by **qualified_name** (module-prefixed for Python), e.g.
`src.db.CodeDB` or `src.processor.CodeProcessor.process` — not the bare name
(`CodeDB`, `process`). Always copy `qualified_name` from tool output into
`get_symbol_context`. Never invent or shorten it.

## Workflow

### Phase 1: Orient
Call `get_directory_tree` first. This gives the full project layout with line
counts and symbol counts per file. Use it to:
- Identify main source directories and entrypoints (e.g. `main.py`, `app.py`)
- Spot high-symbol-count files (likely core modules)
- Understand the project's shape before diving deeper

### Phase 2: Locate
Call `search_symbols` with keywords from the user's request. This FTS-searches
`qualified_name`, signatures, and docstrings.
- Prefer specific terms likely to appear in the codebase
- Copy the **`qualified_name`** from each hit — you need it for Phase 3

### Phase 3: Understand
Call `get_symbol_context` with the exact **`qualified_name`** from Phase 2.
This returns:
- The **definition** (source lines for the indexed span)
- **References** (calls, accesses, type annotations) with file paths and lines
- Use this to trace how a symbol is used across the codebase

### Phase 4: Inspect (optional)
Call `get_file_overview` for one file's imports and full symbol tree (each
node shows `qualified_name`). Useful when:
- You need the full picture of a single file
- You want every symbol in that file, not just one search hit
- `file_path` is relative to the index root with POSIX slashes (e.g. `src/db.py`)

## Rules
- Start with `get_directory_tree` if you lack a directory map.
- Never guess a `qualified_name`. Take it only from `search_symbols` or
  `get_file_overview` output.
- For "where is X defined" or "who calls X", go
  `search_symbols` → `get_symbol_context`.
- Cite file paths and line numbers in every response.
"""


def generate_skill(root: Path | None = None) -> Path:
    base = (root or Path.cwd()).resolve()
    output_path = base / ".claude" / "skills" / "code-parse" / "SKILL.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_SKILL_INSTRUCTIONS, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(generate_skill())
