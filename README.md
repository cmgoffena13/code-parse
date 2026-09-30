# codeparse

Python codebase indexer exposed as an MCP server via the `codeparse` CLI.

## Install as an MCP server

1. Put the `codeparse` binary on your PATH (release asset or `make compile` → `dist/codeparse`).
2. `codeparse --install-mcp`
3. `codeparse create-skill cursor` (all projects) or `codeparse create-skill claude` (current project)
4. Reload the client (or refresh MCP).

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