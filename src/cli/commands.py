import argparse
from pathlib import Path


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cbp", description="cbp")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show CLI version",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show CLI information",
    )
    parser.add_argument(
        "--install-mcp",
        action="store_true",
        help="Register cbp in Cursor and Claude Desktop MCP configs",
    )
    parser.add_argument(
        "--create-skill",
        action="store_true",
        help="Write the Claude Codebase-Parser skill under .claude/skills/",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Workspace root (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command")

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Start the MCP server over stdio",
    )
    mcp_parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Workspace root to index (default: current directory)",
    )

    index_parser = subparsers.add_parser(
        "index",
        help="Index the workspace (incremental by default)",
    )
    index_parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Workspace root to index (default: current directory)",
    )
    index_parser.add_argument(
        "--full-reload",
        action="store_true",
        help="Force a full reparse instead of incremental",
    )

    return parser


def build_arg_parser(argv: list[str] | None = None) -> argparse.Namespace:
    return make_parser().parse_args(argv)
