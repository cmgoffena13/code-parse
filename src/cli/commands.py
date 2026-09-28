import argparse
from pathlib import Path


def build_arg_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="cbp")
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
        help="Workspace root to index (default: current directory)",
    )
    return parser.parse_args()
