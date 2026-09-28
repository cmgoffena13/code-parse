import json
import sys
from pathlib import Path

import pytest

from src.app import main
from src.cli.install_mcp import install_mcp


def test_version_flag_prints_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["cbp", "--version"])
    assert main() == 0
    out = capsys.readouterr().out
    assert "cbp Version:" in out
    assert "0.1.0" in out


def test_info_flag_prints_paths_and_exits_zero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "codebase-parser-config"
    monkeypatch.setenv("CODEBASE_PARSER_CONFIG_DIR", str(config_dir))
    monkeypatch.setattr(sys, "argv", ["cbp", "--info"])
    assert main() == 0
    out = capsys.readouterr().out
    assert "CLI Path:" in out
    assert "Config Directory:" in out
    assert str(config_dir) in out


def test_cwd_missing_directory_exits_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    missing = tmp_path / "no-such-dir"
    monkeypatch.setattr(sys, "argv", ["cbp", "--cwd", str(missing)])
    assert main() == 1
    err = capsys.readouterr().err
    assert "Not a directory" in err


def test_install_mcp_merges_into_cursor_and_claude(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    cursor = tmp_path / "cursor-config" / "mcp.json"
    claude = tmp_path / "claude-config" / "claude_desktop_config.json"
    cursor.parent.mkdir(parents=True)
    cursor.write_text(
        json.dumps({"mcpServers": {"other": {"command": "noop"}}}),
        encoding="utf-8",
    )
    fake_cli = tmp_path / "cbp"
    fake_cli.write_text("#!/bin/sh\n", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["cbp", "--install-mcp"])
    monkeypatch.setattr(
        "src.cli.install_mcp.cursor_mcp_config_path",
        lambda: cursor,
    )
    monkeypatch.setattr(
        "src.cli.install_mcp.claude_desktop_config_path",
        lambda: claude,
    )
    monkeypatch.setattr(
        "src.cli.install_mcp.resolve_cli_path",
        lambda: fake_cli,
    )

    assert main() == 0
    out = capsys.readouterr().out
    assert str(cursor) in out
    assert str(claude) in out
    assert '"cbp"' in out
    assert "${workspaceFolder}" in out

    cursor_data = json.loads(cursor.read_text(encoding="utf-8"))
    assert cursor_data["mcpServers"]["other"]["command"] == "noop"
    assert cursor_data["mcpServers"]["cbp"] == {
        "type": "stdio",
        "command": str(fake_cli.resolve()),
        "args": ["--cwd", "${workspaceFolder}"],
    }

    claude_data = json.loads(claude.read_text(encoding="utf-8"))
    assert claude_data["mcpServers"]["cbp"]["command"] == str(fake_cli.resolve())


def test_install_mcp_permission_error_prints_manual_entry(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    cursor = tmp_path / "cursor.json"
    claude = tmp_path / "claude.json"
    cli = tmp_path / "cbp"
    cli.write_text("x", encoding="utf-8")

    def boom(_self: Path, *_args: object, **_kwargs: object) -> None:
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "write_text", boom)

    written = install_mcp(cli_path=cli, cursor_config=cursor, claude_config=claude)
    assert written == []
    err = capsys.readouterr().err
    assert "Warning: Could not write to" in err
    assert "Manually add this entry:" in err
    assert str(cli.resolve()) in err


def test_install_mcp_helper_writes_absolute_command(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    cursor = tmp_path / "cursor.json"
    claude = tmp_path / "claude.json"
    cli = tmp_path / "bin" / "cbp"
    cli.parent.mkdir()
    cli.write_text("x", encoding="utf-8")

    written = install_mcp(cli_path=cli, cursor_config=cursor, claude_config=claude)
    assert written == [cursor, claude]
    entry = json.loads(cursor.read_text(encoding="utf-8"))["mcpServers"]["cbp"]
    assert entry["command"] == str(cli.resolve())
    out = capsys.readouterr().out
    assert f"Wrote to {cursor}" in out
