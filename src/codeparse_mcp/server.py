import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from src.codeparse_mcp.directory_tree import get_directory_tree as run_directory_tree
from src.codeparse_mcp.file_overview import get_file_overview as run_file_overview
from src.codeparse_mcp.find_importers import find_importers as run_find_importers
from src.codeparse_mcp.search_symbols import search_symbols as run_symbol_search
from src.codeparse_mcp.symbol_context import get_symbol_context as run_symbol_context
from src.db import CodeDB
from src.processor import CodeProcessor
from src.utils import get_code_parse_config_dir

_INSTRUCTIONS = """\
codeparse tools read an up-to-date SQLite code index. 
The index is automatically refreshed on every tool call to reflect recent file changes. 
Start the server in the repository you want to index.
"""


def index_root() -> Path:
    # Claude Desktop passes workspace via env var
    workspace = os.environ.get("CLAUDE_WORKSPACE", "").strip()
    if workspace:
        return Path(workspace).resolve()
    # VS Code / Terminal passes it via CWD
    return Path.cwd().resolve()


@asynccontextmanager
async def _lifespan(_app: MCPServer) -> AsyncIterator[dict[str, Any]]:
    get_code_parse_config_dir()
    root = index_root()
    db = CodeDB(root)
    processor = CodeProcessor(db, root)
    processor.process()
    try:
        yield {"db": db, "processor": processor}
    finally:
        db.close()


mcp = MCPServer("codeparse", instructions=_INSTRUCTIONS, lifespan=_lifespan)


def _processor(ctx: Context) -> CodeProcessor:
    return ctx.request_context.lifespan_context["processor"]


@mcp.tool()
def get_directory_tree(ctx: Context, path: str | None = None) -> str:
    """
    Return the repo's directory/file tree with line and symbol counts.
    Optional ``path`` scopes to one directory tree (exact path).
    Do not call this repeatedly in one task.
    """
    return _processor(ctx).run_query(lambda db: run_directory_tree(db, path=path))


@mcp.tool()
def get_file_overview(file_path: str, ctx: Context) -> str:
    """
    Return imports and a nested symbol tree for one file (``qualified_name`` + line count).
    Use ``get_symbol_context`` for definitions.
    """
    path = file_path.strip()
    return _processor(ctx).run_query(lambda db: run_file_overview(db, path))


@mcp.tool()
def search_symbols(
    query: str,
    ctx: Context,
    limit: int = 10,
    include_tests: bool = False,
) -> str:
    """
    Full-text search across symbols (``qualified_name``, signatures, and docstrings).
    Excludes test files by default. Set ``include_tests`` to include them.
    Example queries: ``transpile``, ``loader OR load``, ``dialect AND format``
    """
    return _processor(ctx).run_query(
        lambda db: run_symbol_search(
            db,
            query,
            limit,
            include_tests=include_tests,
        )
    )


@mcp.tool()
def get_symbol_context(
    qualified_name: str,
    ctx: Context,
    include_references: bool = False,
) -> str:
    """
    Return the symbol definition (source lines).
    Excludes references (calls, accesses, type annotations) by default. Set ``include_references`` to include them.
    Use instead of ``read`` to get symbol definitions.
    """
    name = qualified_name.strip()
    return _processor(ctx).run_query(
        lambda db: run_symbol_context(db, name, include_references=include_references)
    )


@mcp.tool()
def find_importers(file_path: str, ctx: Context, include_tests: bool = False) -> str:
    """
    Return files that import a given module file as ``• path:line - symbols``.
    Excludes test files by default; set ``include_tests`` to include them.
    Use for who-imports / dependency fan-in.
    """
    path = file_path.strip()
    return _processor(ctx).run_query(
        lambda db: run_find_importers(db, path, include_tests=include_tests)
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
