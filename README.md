# CodeParse

CodeParse is a codebase indexer that gives agents fast, accurate, and compact context on your Python codebases while reducing token usage.

## Install as an MCP server

1. Put the `codeparse` binary on your PATH (release asset or `make compile` → `dist/codeparse`).
2. `codeparse --install-mcp`
3. `codeparse create-skill cursor` (all projects) or `codeparse create-skill claude` (current project)
4. Reload the client (or refresh MCP).

## Benchmark Evaluation (in-progress)

Ten Questions found in `eval/tasks.json` are evaluated against the [SQLMesh](https://github.com/TobikoData/sqlmesh) repo using a baseline agent and an agent with the CodeParse MCP server.

```
Cursor Benchmark Evaluation - Grok 4.7
----------------- Mean -----------------
Baseline Tokene: 337,737
Baseline Tool Calls: 20
CodeParse Tokens: 198,469 (59%)
CodeParse Tool Calls: 11 (%56)
----------------------------------------
```

### Running the Evaluation

Cursor Default Model: `grok 4.7`  
Claude Defualt Model: `opus 5.5 medium`

 - `make eval-smoke cursor` will run all 10 questions and evaluate.
 - `make eval cursor` will run all 10 questions on repeat (10 times) and evaluate. 

