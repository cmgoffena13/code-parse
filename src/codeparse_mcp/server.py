import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import Context, MCPServer

from src.codeparse_mcp.directory_tree import get_directory_tree as run_directory_tree
from src.codeparse_mcp.file_overview import get_file_overview as run_file_overview
from src.codeparse_mcp.search_symbols import search_symbols as run_symbol_search
from src.codeparse_mcp.symbol_context import get_symbol_context as run_symbol_context
from src.db import CodeDB
from src.processor import CodeProcessor
from src.utils import get_code_parse_config_dir

_INSTRUCTIONS = """\
Code-Parse tools read an up-to-date SQLite code index. The index is automatically refreshed
incrementally on every tool call to reflect recent file changes.
Prefer these tools for code analysis over generic file reading or grep search.
Symbols are identified by ``qualified_name`` (module-prefixed for Python);
copy it from ``search_symbols`` or ``get_file_overview`` into ``get_symbol_context``.
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


mcp = MCPServer("code-parse", instructions=_INSTRUCTIONS, lifespan=_lifespan)


def _processor(ctx: Context) -> CodeProcessor:
    return ctx.request_context.lifespan_context["processor"]


@mcp.tool()
def get_directory_tree(ctx: Context) -> str:
    """Return the full directory/file tree of the indexed codebase with line counts
    and symbol counts per file. Use this at the start of a session to understand project structure
    before drilling into specific files or symbols."""
    return _processor(ctx).run_query(run_directory_tree)


@mcp.tool()
def get_file_overview(file_path: str, ctx: Context) -> str:
    """Return imports and a symbol tree for a single file. Each symbol is labeled
    with its ``qualified_name`` (module-prefixed for Python), which you can pass
    to ``get_symbol_context``. ``file_path`` is relative to the index root using
    POSIX slashes, e.g. ``src/db.py``. Use after ``get_directory_tree`` to inspect
    a specific file."""
    path = file_path.strip()
    return _processor(ctx).run_query(lambda db: run_file_overview(db, path))


@mcp.tool()
def search_symbols(query: str, ctx: Context, limit: int = 20) -> str:
    """Full-text search across indexed symbols (``qualified_name``, signatures,
    docstrings). Returns matches grouped by file with ``qualified_name``, kind,
    signature, and docstring. Pass that exact ``qualified_name`` to
    ``get_symbol_context`` — do not use a bare name. Example queries: ``memory``,
    ``CodeProcessor.process``, ``db_path_for_index_root``."""
    return _processor(ctx).run_query(lambda db: run_symbol_search(db, query, limit))


@mcp.tool()
def get_symbol_context(qualified_name: str, ctx: Context) -> str:
    """Return the definition (source lines) and all references (calls, accesses,
    type annotations) for one symbol. ``qualified_name`` must match
    ``symbols.qualified_name`` exactly — copy it from ``search_symbols`` or
    ``get_file_overview``, e.g. ``src.db.CodeDB`` or
    ``src.processor.CodeProcessor.process``. Bare names like ``CodeDB`` will not
    match. Includes file paths and line numbers for every reference."""
    name = qualified_name.strip()
    return _processor(ctx).run_query(lambda db: run_symbol_context(db, name))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
