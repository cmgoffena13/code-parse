"""Install codeparse as an MCP server in known client configs."""

import json
import os
import sys
from pathlib import Path
from typing import Any

SERVER_KEY = "codeparse"

# Cursor expands this at runtime to the open project root. Kept as a literal
# JSON string (no extra brace escaping) — ``json.dumps`` writes it unchanged.
CURSOR_WORKSPACE_ARG = "${workspaceFolder}"


def resolve_cli_path() -> Path:
    """Absolute path to the running ``codeparse`` binary."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(sys.argv[0]).resolve()


def cursor_mcp_config_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


def claude_desktop_config_path() -> Path:
    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise TypeError(f"MCP config is not a JSON object: {path}")
    return data


def merge_mcp_server(config_path: Path, entry: dict[str, Any]) -> bool:
    """
    Upsert ``SERVER_KEY`` under ``mcpServers`` and write the config file.

    Returns True on success. On ``PermissionError``, prints a warning plus the
    entry for manual install and returns False.
    """
    entry_json = json.dumps({SERVER_KEY: entry}, indent=2)
    try:
        config = _load_config(config_path)
        servers = config.setdefault("mcpServers", {})
        if not isinstance(servers, dict):
            raise TypeError(f"mcpServers must be an object: {config_path}")
        servers[SERVER_KEY] = entry
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    except PermissionError as e:
        print(f"Warning: Could not write to {config_path}: {e}", file=sys.stderr)
        print("Manually add this entry:", file=sys.stderr)
        print(entry_json, file=sys.stderr)
        return False

    print(f"Wrote to {config_path}:\n{entry_json}")
    return True


def install_mcp(
    *,
    cli_path: Path | None = None,
    cursor_config: Path | None = None,
    claude_config: Path | None = None,
) -> list[Path]:
    """
    Register ``codeparse`` in Cursor (global) and Claude Desktop configs.

    Cursor gets ``mcp --cwd ${workspaceFolder}`` so one install follows the open
    project (Cursor expands the variable). Claude Desktop gets ``mcp`` and relies
    on ``CLAUDE_WORKSPACE`` / process cwd.
    """
    cli = (cli_path or resolve_cli_path()).resolve()
    written: list[Path] = []

    cursor_path = cursor_config or cursor_mcp_config_path()
    cursor_entry = {
        "type": "stdio",
        "command": str(cli),
        "args": ["mcp", "--cwd", CURSOR_WORKSPACE_ARG],
    }
    if merge_mcp_server(cursor_path, cursor_entry):
        written.append(cursor_path)

    claude_path = claude_config or claude_desktop_config_path()
    claude_entry = {
        "command": str(cli),
        "args": ["mcp"],
    }
    if merge_mcp_server(claude_path, claude_entry):
        written.append(claude_path)

    return written
