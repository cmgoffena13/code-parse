"""Smoke-print MCP tool outputs against the eval SQLMesh checkout."""

from pathlib import Path

from src.codeparse_mcp.directory_tree import get_directory_tree
from src.codeparse_mcp.file_overview import get_file_overview
from src.codeparse_mcp.find_importers import find_importers
from src.codeparse_mcp.find_subclasses import find_subclasses
from src.codeparse_mcp.project_overview import get_project_overview
from src.codeparse_mcp.search_symbols import search_symbols
from src.codeparse_mcp.symbol_context import get_symbol_context
from src.db import CodeDB
from src.processor import CodeProcessor

REPO_ROOT = Path(__file__).resolve().parent
SQLMESH_ROOT = REPO_ROOT / "eval" / "cache" / "sqlmesh"

_BANNER_WIDTH = 40


def _banner(title: str) -> str:
    label = f" {title} "
    pad = max(_BANNER_WIDTH - len(label), 0)
    left = pad // 2
    right = pad - left
    return f"{'-' * left}{label}{'-' * right}"


def _print_section(title: str, body: str) -> None:
    print(_banner(title))
    print(body)
    print(f"[{len(body):,} chars / {body.count(chr(10)) + 1} lines]\n")


def main() -> None:
    if not SQLMESH_ROOT.is_dir():
        raise SystemExit(
            f"Missing {SQLMESH_ROOT}; run an eval smoke first to clone sqlmesh."
        )

    db = CodeDB(SQLMESH_ROOT)
    processor = CodeProcessor(db, SQLMESH_ROOT)
    processor.process(full=True)

    _print_section("DIRECTORY TREE", get_directory_tree(db, "sqlmesh/core/"))
    _print_section("FILE OVERVIEW", get_file_overview(db, "sqlmesh/core/dialect.py"))
    _print_section("SEARCH SYMBOLS", search_symbols(db, "format_model"))
    _print_section(
        "SYMBOL CONTEXT",
        get_symbol_context(
            db,
            "sqlmesh.core.dialect.format_model_expressions",
            include_references=True,
        ),
    )
    _print_section("FIND IMPORTERS", find_importers(db, "sqlmesh/core/dialect.py"))
    _print_section(
        "FIND SUBCLASSES",
        find_subclasses(db, "sqlmesh.core.snapshot.evaluator.EvaluationStrategy"),
    )
    _print_section("PROJECT OVERVIEW", get_project_overview(db))


if __name__ == "__main__":
    main()
