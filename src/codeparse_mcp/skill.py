from pathlib import Path
from typing import Literal

SkillTarget = Literal["claude", "cursor"]

SKILL_INSTRUCTIONS = """\
---
name: codeparse
description: Use the codeparse MCP Server effectively.
allowed-tools: get_directory_tree get_file_overview search_symbols get_symbol_context get_symbol_references find_importers find_subclasses get_project_overview
---

IMPORTANT: ALWAYS USE ``get_symbol_context`` / ``get_file_overview`` instead of ``read`` to get file / symbol information.

The information that is provided to you will determine the tool you should use.

## You are given the file name.
1. Use ``get_file_overview`` to get a summary of the symbols in the file.
2. Use ``get_symbol_context`` to get the code definition of the symbol. 

## You are given the file name and exact symbol name.
1. Use ``get_symbol_context`` to get the code definition of the symbol. 

## You are NOT given the file name or exact symbol name. 
1. Investigate the codebase using ``get_project_overview`` and keywords. 
2. Use ``get_file_overview`` to get a summary of the symbols in the file.
3. Use ``get_symbol_context`` to get the code definition of the symbol.

## How to investigate the codebase using keywords

### ``glob``
 - Use when the clue is a path or a file name.
 - DO NOT glob for specific directory files; use ``get_directory_tree`` with the path.

### ``grep``
 - Use when the clue is specific text in file contents.
 - DO NOT grep for symbol names; use ``search_symbols``.
 - DO NOT grep for import statements; use ``find_importers``.
 - DO NOT grep for reference sites of a known symbol; use ``get_symbol_references``.

### ``search_symbols``
 - Use when the clue is part of a symbol name, signature, or docstring.
 - Set the limit to 5 if you know the local symbol name, but need the qualified name.
"""


def generate_skill(
    target: SkillTarget,
    *,
    root: Path | None = None,
    cursor_skills_base: Path | None = None,
) -> Path:
    """Write the codeparse skill for ``claude`` (project) or ``cursor`` (user-global).

    - ``claude`` → ``{root}/.claude/skills/codeparse/SKILL.md``
    - ``cursor`` → ``~/.cursor/skills/codeparse/SKILL.md`` (all projects)
    """
    if target == "claude":
        base = (root or Path.cwd()).resolve()
        output_path = base / ".claude" / "skills" / "codeparse" / "SKILL.md"
    elif target == "cursor":
        base = (cursor_skills_base or (Path.home() / ".cursor" / "skills")).resolve()
        output_path = base / "codeparse" / "SKILL.md"
    else:
        raise ValueError(f"unknown skill target: {target!r}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SKILL_INSTRUCTIONS, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2 or sys.argv[1] not in ("claude", "cursor"):
        print(f"Usage: {sys.argv[0]} claude|cursor", file=sys.stderr)
        raise SystemExit(2)
    print(generate_skill(sys.argv[1]))
