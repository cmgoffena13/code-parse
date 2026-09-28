# codebase-parse

Python codebase indexer exposed as an MCP server via the `cbp` CLI.

## Install as an MCP server

1. Get the `cbp` binary (release asset or `make compile` → `dist/cbp`).
2. Make sure the binary is on your PATH
3. Run:

```bash
cbp --install-mcp
```

That registers `cbp` in:

- **Cursor** — `~/.cursor/mcp.json` with `--cwd ${workspaceFolder}` so it indexes whatever project you have open
- **Claude Desktop** — the platform Claude config file (uses `CLAUDE_WORKSPACE` / process cwd)

> The command prints the JSON it wrote so you can verify. If a config directory isn't writable, it prints a warning and the entry to paste in manually. If your client does **not** expand `${workspaceFolder}`, replace that arg with an absolute project path instead, e.g. `"args": ["--cwd", "/path/to/repo"]`.

4. Reload the client (or refresh MCP) so it picks up the new server.

Indexes are stored under `~/.config/codebase-parser/databases/`.

## CLI

```bash
cbp --version
cbp --info
cbp --install-mcp
cbp --create-skill          # write .claude/skills/codebase-parse/SKILL.md
cbp --full-reload           # force full reparse of --cwd (default: .)
cbp --cwd /path/to/repo     # start MCP over stdio for that root
```

With no flags, `cbp` starts the MCP server over stdio for the current directory.
