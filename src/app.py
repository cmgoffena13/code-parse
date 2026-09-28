import os
import sys
from pathlib import Path

from src.cli.commands import build_arg_parser
from src.utils import get_codebase_parser_config_dir, get_version


def main() -> int:
    args = build_arg_parser()
    if args.info:
        cli_path = Path(sys.argv[0]).resolve()
        print(f"CLI Path: {cli_path}")
        print(f"Config Directory: {get_codebase_parser_config_dir()}")
        return 0
    if args.version:
        print(f"cbp Version: {get_version()}")
        return 0
    if args.install_mcp:
        from src.cli.install_mcp import install_mcp

        written = install_mcp()
        if written:
            print("Restart the client (or reload MCP) to pick up the change.")
            return 0
        return 1

    cwd = args.cwd.resolve()
    if not cwd.is_dir():
        print(f"Not a directory: {cwd}", file=sys.stderr)
        return 1
    os.chdir(cwd)

    from src.mcp.server import mcp

    mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
