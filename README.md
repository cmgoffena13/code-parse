# codebase-parse

Python codebase indexer exposed as an MCP server via the `cbp` CLI.

## Install as an MCP server

1. Get the `cbp` binary (release asset or `make compile` → `dist/cbp`).
2. Make sure the binary is on your PATH
3. Run:

```bash
cbp --install-mcp
```

That registers `cbp mcp` in:

- **Cursor** — `~/.cursor/mcp.json` with `mcp --cwd ${workspaceFolder}` so it indexes whatever project you have open
- **Claude Desktop** — `mcp` (uses `CLAUDE_WORKSPACE` / process cwd)

> The command prints the JSON it wrote so you can verify. If a config directory isn't writable, it prints a warning and the entry to paste in manually. If your client does **not** expand `${workspaceFolder}`, replace that arg with an absolute project path instead, e.g. `"args": ["mcp", "--cwd", "/path/to/repo"]`.

4. Reload the client (or refresh MCP) so it picks up the new server.

Indexes are stored under `~/.config/codebase-parse/indexes/`.

## Claude Skill

Use `cbp --create-skill` to write `.claude/skills/codebase-parse/SKILL.md`. The skill steers Claude to prefer the MCP tools — orient with the tree, search by `qualified_name`, then pull symbol context — instead of reading or grepping the entire codebase.
