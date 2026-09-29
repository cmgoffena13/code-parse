import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from src.codeparse_mcp.directory_tree import get_directory_tree as run_directory_tree
from src.codeparse_mcp.file_overview import get_file_overview as run_file_overview
from src.codeparse_mcp.find_importers import find_importers as run_find_importers
from src.codeparse_mcp.find_paths import find_paths as run_find_paths
from src.codeparse_mcp.search_symbols import search_symbols as run_symbol_search
from src.codeparse_mcp.symbol_context import get_symbol_context as run_symbol_context
from src.db import CodeDB
from src.processor import CodeProcessor
from src.utils import get_code_parse_config_dir

_INSTRUCTIONS = """\
codeparse tools read an up-to-date SQLite code index. The index is automatically refreshed
incrementally on every tool call to reflect recent file changes. Start the server in the repository you want to index.
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
def get_directory_tree(ctx: Context) -> str:
    """Return the FULL indexed directory/file tree with line and symbol counts.
    If the user already named a package or file, call ``get_file_overview`` or ``search_symbols`` instead.
    Do not call this repeatedly in one task."""
    return _processor(ctx).run_query(run_directory_tree)


@mcp.tool()
def find_paths(pattern: str, ctx: Context, limit: int = 50) -> str:
    """Find indexed file/directory paths by glob-style pattern (e.g. ``*dialect*``,
    ``sqlmesh/core/*.py``). Prefer this over ``get_directory_tree`` when hunting
    for a path. Does not search file contents."""
    return _processor(ctx).run_query(
        lambda db: run_find_paths(db, pattern, limit=limit)
    )


@mcp.tool()
def get_file_overview(file_path: str, ctx: Context) -> str:
    """Return imports and a symbol tree for one file. Each symbol includes its
    ``qualified_name`` for ``get_symbol_context``."""
    path = file_path.strip()
    return _processor(ctx).run_query(lambda db: run_file_overview(db, path))


@mcp.tool()
def search_symbols(
    query: str, ctx: Context, limit: int = 10, include_tests: bool = False
) -> str:
    """Full-text search across indexed symbols (``qualified_name``, signatures,
    docstrings). By default excludes ``is_test`` symbols; set ``include_tests``
    to search those too. Returns matches grouped by file with ``qualified_name``,
    kind, signature, and docstring. Example queries: ``memory``, ``loader OR load``"""
    return _processor(ctx).run_query(
        lambda db: run_symbol_search(db, query, limit, include_tests=include_tests)
    )


@mcp.tool()
def get_symbol_context(qualified_name: str, ctx: Context) -> str:
    """Return the symbol definition (source lines) and all references (calls, accesses,
    type annotations)."""
    name = qualified_name.strip()
    return _processor(ctx).run_query(lambda db: run_symbol_context(db, name))


@mcp.tool()
def find_importers(file_path: str, ctx: Context) -> str:
    """Return every indexed file that imports a given module file.
    Use for who-imports / dependency fan-in."""
    path = file_path.strip()
    return _processor(ctx).run_query(lambda db: run_find_importers(db, path))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
