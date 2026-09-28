"""
Test Run the Parser.
"""

from pathlib import Path

from src.db import CodeDB
from src.mcp.directory_tree import get_directory_tree
from src.mcp.file_overview import get_file_overview
from src.mcp.search_symbols import search_symbols
from src.mcp.symbol_context import get_symbol_context
from src.processor import CodeProcessor

PROJECT_ROOT = Path(__file__).resolve().parent

_BANNER_WIDTH = 40


def _banner(title: str) -> str:
    label = f" {title} "
    pad = max(_BANNER_WIDTH - len(label), 0)
    left = pad // 2
    right = pad - left
    return f"{'-' * left}{label}{'-' * right}"


def main():
    db = CodeDB(PROJECT_ROOT)
    processor = CodeProcessor(db, PROJECT_ROOT)
    processor.process(full=True)
    print(_banner("DIRECTORY TREE"))
    print(get_directory_tree(db))
    print("\n")
    print(_banner("FILE OVERVIEW"))
    print(get_file_overview(db, "src/db.py"))
    print("\n")
    print(_banner("SEARCH SYMBOLS"))
    print(search_symbols(db, "git"))
    print("\n")
    print(_banner("SYMBOL CONTEXT"))
    print(get_symbol_context(db, "src.git_utils.path_spec_for_indexing"))
    print("\n")


if __name__ == "__main__":
    main()
