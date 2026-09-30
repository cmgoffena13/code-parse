# codeparse

Python codebase indexer exposed as an MCP server via the `codeparse` CLI.

## Install as an MCP server

1. Get the `codeparse` binary (release asset or `make compile` → `dist/codeparse`).
2. Make sure the binary is on your PATH
3. Run `codeparse --install-mcp`
4. Reload the client (or refresh MCP) so it picks up the new server.

## Agent skill

```bash
codeparse create-skill claude   # .claude/skills/codeparse/ under the project (--cwd)
codeparse create-skill cursor   # ~/.cursor/skills/codeparse/ (all projects)
```

The skill teaches when to use each MCP tool (`search_symbols`, `get_file_overview`, `get_symbol_context`, `find_importers`, `get_directory_tree`) and to prefer those over `read` for file and symbol contents.

## Benchmark (in-progress)

Ten Questions found in `eval/tasks.json` are evaluated against a baseline agent and an agent with the MCP server.

Cursor Default Model: `grok 4.7`
Claude Defualt Model: `opus 5.5 medium`

 - `make eval-smoke` will run all 10 questions and evaluate (default: Cursor).
 - `make eval` will run all 10 questions on repeat (10 times) and evaluate (default: Cursor). 

When I remove the ``read`` command for Cursor (to make it stop being dumb) and all tests pass:
```
Overall median (of per-task passing medians)
  baseline : 172,417 tokens  (16 tools)
  codeparse: 107,161 tokens  (8 tools)
  ratio    : 0.62x tokens  0.48x tools  (codeparse / baseline)
Overall mean (of per-task passing medians)
  baseline : 570,117 tokens  (23 tools)
  codeparse: 213,169 tokens  (12 tools)
  ratio    : 0.37x tokens  0.51x tools  (codeparse / baseline)
  * token medians marked with * include failed runs (no passes yet)
  elapsed  : 33m 15s
```