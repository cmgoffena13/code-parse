# codeparse

Python codebase indexer exposed as an MCP server via the `codeparse` CLI.

## Install as an MCP server

1. Get the `codeparse` binary (release asset or `make compile` → `dist/codeparse`).
2. Make sure the binary is on your PATH
3. Run `codeparse --install-mcp`
4. Reload the client (or refresh MCP) so it picks up the new server.

## Claude Skill

Use `codeparse --create-skill` to write `.claude/skills/codeparse/SKILL.md`. The skill steers Claude to prefer the MCP tools — orient with the tree, search by `qualified_name`, then pull symbol context — instead of reading or grepping the entire codebase.

## Benchmark

Ten Questions found in `eval/tasks.json` are evaluated against a baseline agent and an agent with the MCP server.

`make eval-smoke` will run all 10 questions and evaluate.

`make eval` will run all 10 questions on repeat (10 times) and evaluate.