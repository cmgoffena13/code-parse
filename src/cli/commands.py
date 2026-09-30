import argparse
from pathlib import Path


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codeparse", description="codeparse")
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
        help="Register codeparse in Cursor and Claude Desktop MCP configs",
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Workspace root (default: current directory)",
    )

    subparsers = parser.add_subparsers(dest="command")

    create_skill_parser = subparsers.add_parser(
        "create-skill",
        help="Write the codeparse agent skill for Cursor or Claude",
    )
    create_skill_parser.add_argument(
        "target",
        choices=("cursor", "claude"),
        help=(
            "cursor: ~/.cursor/skills/codeparse/ (all projects); "
            "claude: .claude/skills/codeparse/ under --cwd"
        ),
    )
    create_skill_parser.add_argument(
        "--cwd",
        type=Path,
        default=Path.cwd(),
        help="Project root for the Claude skill (ignored for cursor)",
    )

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
