# codeparse

Python codebase indexer exposed as an MCP server via the `codeparse` CLI.

## Install as an MCP server

1. Get the `codeparse` binary (release asset or `make compile` → `dist/codeparse`).
2. Make sure the binary is on your PATH
3. Run `codeparse --install-mcp`
4. Reload the client (or refresh MCP) so it picks up the new server.

## Claude Skill

Use `codeparse --create-skill` to write `.claude/skills/codeparse/SKILL.md`. The skill steers Claude to prefer the MCP tools — orient with the tree, search by `qualified_name`, then pull symbol context — instead of reading or grepping the entire codebase.