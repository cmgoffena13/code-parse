# code-parse

Python codebase indexer exposed as an MCP server via the `codeparse` CLI.

## Install as an MCP server

1. Get the `codeparse` binary (release asset or `make compile` → `dist/codeparse`).
2. Make sure the binary is on your PATH
3. Run `codeparse --install-mcp`

That registers `codeparse mcp` in:

- **Cursor** — `~/.cursor/mcp.json` with `mcp --cwd ${workspaceFolder}`, whatever project you have open
- **Claude Desktop** — `mcp` (uses `CLAUDE_WORKSPACE` / process cwd)

4. Reload the client (or refresh MCP) so it picks up the new server.

## Claude Skill

Use `codeparse --create-skill` to write `.claude/skills/code-parse/SKILL.md`. The skill steers Claude to prefer the MCP tools — orient with the tree, search by `qualified_name`, then pull symbol context — instead of reading or grepping the entire codebase.
