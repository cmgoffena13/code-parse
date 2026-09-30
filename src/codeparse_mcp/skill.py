from pathlib import Path

SKILL_INSTRUCTIONS = """\
---
name: codeparse
description: Use the codeparse MCP Server effectively.
allowed-tools: get_directory_tree get_file_overview search_symbols get_symbol_context find_importers
---

# IMPORTANT
 - Only call tools to get enough information to accomplish the task.
 - Do not call tools to get more information on related symbols unless absolutely necessary.
 - ALWAYS USE ``get_symbol_context`` / ``get_file_overview`` instead of ``read`` to get symbol information.

The information that is provided to you will determine the tool you should use.

## You are given the file name.
1. Use ``get_file_overview`` to get a summary of the symbols in the file.
2. Use ``get_symbol_context`` to get the code of the symbol. 

## You are given the file name and symbol name.
1. Use ``get_symbol_context`` to get the code of the symbol. 

## You are NOT given the file name or symbol name. 
1. Investigate the codebase using keywords. 
2. Use ``get_file_overview`` to get a summary of the symbols in the file.
3. Use ``get_symbol_context`` to get the code of the symbol.

## How to investigate the codebase using keywords
 - Use ``glob`` when the clue is a path or a file name.
 - Use ``grep`` when the clue is text in file contents.
 - Use ``search_symbols`` when the clue is a symbol name or phrase referencing a symbol.

## When to use ``find_importers``
 - You need to find all the files that import a given file or symbol.

## When to use ``get_directory_tree``
 - You need to get a summary of the codebase.
 - You need to get a summary of the files in a given directory.
"""


def generate_skill(root: Path | None = None) -> Path:
    base = (root or Path.cwd()).resolve()
    output_path = base / ".claude" / "skills" / "codeparse" / "SKILL.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(SKILL_INSTRUCTIONS, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(generate_skill())
