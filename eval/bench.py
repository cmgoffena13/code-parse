#!/usr/bin/env python3
"""Token-usage benchmark: codeparse MCP vs read/grep on a pinned SQLMesh checkout.

Supports --provider cursor (Cursor SDK) or claude (Claude Agent SDK).
"""

import argparse
import asyncio
import json
import os
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.codeparse_mcp.skill import SKILL_INSTRUCTIONS

EVAL_DIR = REPO_ROOT / "eval"
TASKS_PATH = EVAL_DIR / "tasks.json"
CACHE_DIR = EVAL_DIR / "cache"
RESULTS_DIR = EVAL_DIR / "results"
SQLMESH_DIR = CACHE_DIR / "sqlmesh"

DEFAULT_MODELS = {
    "cursor": "grok-4.7",
    "claude": "claude-opus-5-5-medium",
}

ANSWER_FORMAT = """\
Follow the exact field labels requested in the question. Put each field on its own line.
Do not invent paths. Prefer precise qualified names when the tools provide them.
"""

CURSOR_DISALLOWED = ["shell", "task", "webSearch", "edit"]

# Claude Code built-ins that would break a fair read/grep or MCP-only baseline.
CLAUDE_DISALLOWED_WRITE = [
    "Bash",
    "Write",
    "Edit",
    "NotebookEdit",
    "WebSearch",
    "WebFetch",
    "Agent",
    "Task",
    "Skill",
    "SlashCommand",
]
CLAUDE_DISALLOWED_READ = ["Read", "Grep", "Glob", "LS"]


def _load_tasks() -> dict[str, Any]:
    return json.loads(TASKS_PATH.read_text(encoding="utf-8"))


def ensure_sqlmesh(sha: str, repo_url: str) -> Path:
    if not SQLMESH_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", repo_url, str(SQLMESH_DIR)],
            check=True,
        )
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=SQLMESH_DIR,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current != sha:
        subprocess.run(
            ["git", "fetch", "--depth", "1", "origin", sha], cwd=SQLMESH_DIR, check=True
        )
        subprocess.run(["git", "checkout", "--force", sha], cwd=SQLMESH_DIR, check=True)
    return SQLMESH_DIR.resolve()


def index_sqlmesh(sqlmesh: Path) -> None:
    subprocess.run(
        [
            "uv",
            "run",
            "--directory",
            str(REPO_ROOT),
            "--",
            "python",
            "-m",
            "src.app",
            "index",
            "--cwd",
            str(sqlmesh),
        ],
        check=True,
    )


def grade(
    answer: str,
    must_contain: list[str],
    must_contain_any: list[list[str]] | None = None,
) -> tuple[bool, list[str]]:
    missing = [item for item in must_contain if item not in answer]
    for group in must_contain_any or []:
        if not any(item in answer for item in group):
            missing.append(f"any_of:{'|'.join(group)}")
    return (not missing, missing)


def _cursor_usage_dict(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "cache_write_tokens": usage.cache_write_tokens,
        "total_tokens": usage.total_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
    }


def _claude_usage_dict(usage: dict[str, Any] | None) -> dict[str, Any] | None:
    if not usage:
        return None
    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    cache_read = int(usage.get("cache_read_input_tokens") or 0)
    cache_write = int(usage.get("cache_creation_input_tokens") or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "total_tokens": input_tokens + output_tokens + cache_read + cache_write,
        "reasoning_tokens": None,
    }


def _mcp_server_args(sqlmesh: Path) -> list[str]:
    return [
        "run",
        "--directory",
        str(REPO_ROOT),
        "--",
        "python",
        "-m",
        "src.app",
        "mcp",
        "--cwd",
        str(sqlmesh),
    ]


def build_prompt(task: dict[str, Any], *, arm: str) -> str:
    parts = [
        f"Repository root: {SQLMESH_DIR.resolve()}",
        "You are answering one benchmark question about this checkout.",
        task["prompt"],
        ANSWER_FORMAT,
    ]
    if arm == "codeparse":
        parts.insert(
            0,
            "You must use the codeparse MCP tools. Follow this skill:\n\n"
            + SKILL_INSTRUCTIONS,
        )
    else:
        parts.insert(
            0,
            "You may only use read/grep/glob/ls. Do not invent file contents.",
        )
    return "\n\n".join(parts)


def _count_cursor_tool_calls(run: Any) -> int:
    from cursor_sdk.types import AgentConversationTurn, ToolCallConversationStep

    try:
        turns = run.conversation()
    except Exception:  # noqa: BLE001 — conversation may be unavailable
        return 0
    count = 0
    for wrap in turns:
        turn = getattr(wrap, "turn", wrap)
        steps = getattr(turn, "steps", None)
        if steps is None and isinstance(turn, dict):
            steps = turn.get("steps") or []
        if not isinstance(turn, AgentConversationTurn) and steps is None:
            continue
        for step in steps or ():
            is_tool = (
                isinstance(step, ToolCallConversationStep)
                or getattr(step, "type", None) == "toolCall"
            )
            if not is_tool and isinstance(step, dict):
                is_tool = step.get("type") == "toolCall"
            if is_tool:
                count += 1
    return count


def run_cursor_agent(
    *,
    arm: str,
    prompt: str,
    model: str,
    api_key: str,
    sqlmesh: Path,
) -> tuple[str, str | None, dict[str, Any] | None, str, int]:
    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions
    from cursor_sdk.types import StdioMcpServerConfig

    if arm == "baseline":
        options = AgentOptions(
            model=model,
            api_key=api_key,
            tools=["read", "grep", "glob", "ls"],
            disallowed_tools=CURSOR_DISALLOWED,
            local=LocalAgentOptions(cwd=str(sqlmesh), setting_sources=[]),
        )
    elif arm == "codeparse":
        options = AgentOptions(
            model=model,
            api_key=api_key,
            tools=["mcp"],
            disallowed_tools=CURSOR_DISALLOWED,
            mcp_servers={
                "codeparse": StdioMcpServerConfig(
                    command="uv",
                    args=_mcp_server_args(sqlmesh),
                )
            },
            local=LocalAgentOptions(cwd=str(sqlmesh), setting_sources=[]),
        )
    else:
        raise ValueError(f"unknown arm: {arm}")

    with Agent.create(options) as agent:
        run = agent.send(prompt)
        result = run.wait()
        status = result.status
        text = run.text() if status == "finished" else ""
        if not text and hasattr(result, "result") and result.result:
            text = str(result.result)
        usage = _cursor_usage_dict(
            result.usage if result.usage is not None else run.usage
        )
        run_id = getattr(result, "id", None) or getattr(run, "id", None)
        tool_calls = _count_cursor_tool_calls(run)
        return text, str(run_id) if run_id else None, usage, str(status), tool_calls


async def _run_claude_query(
    *,
    arm: str,
    prompt: str,
    model: str,
    sqlmesh: Path,
) -> tuple[str, str | None, dict[str, Any] | None, str, int]:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        query,
    )

    if arm == "baseline":
        options = ClaudeAgentOptions(
            model=model,
            cwd=str(sqlmesh),
            tools=["Read", "Grep", "Glob", "LS"],
            allowed_tools=["Read", "Grep", "Glob", "LS"],
            disallowed_tools=CLAUDE_DISALLOWED_WRITE,
            permission_mode="bypassPermissions",
            setting_sources=[],
            strict_mcp_config=True,
        )
    elif arm == "codeparse":
        options = ClaudeAgentOptions(
            model=model,
            cwd=str(sqlmesh),
            mcp_servers={
                "codeparse": {
                    "command": "uv",
                    "args": _mcp_server_args(sqlmesh),
                }
            },
            allowed_tools=["mcp__codeparse__*"],
            disallowed_tools=CLAUDE_DISALLOWED_WRITE + CLAUDE_DISALLOWED_READ,
            permission_mode="bypassPermissions",
            setting_sources=[],
            strict_mcp_config=True,
        )
    else:
        raise ValueError(f"unknown arm: {arm}")

    text_parts: list[str] = []
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    status = "finished"
    result_text = ""
    tool_calls = 0
    num_turns: int | None = None

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
                elif isinstance(block, ToolUseBlock):
                    tool_calls += 1
        elif isinstance(message, ResultMessage):
            session_id = message.session_id
            usage = _claude_usage_dict(
                message.usage if isinstance(message.usage, dict) else None
            )
            num_turns = message.num_turns
            if message.result:
                result_text = message.result
            if message.is_error or (
                message.subtype and message.subtype not in ("success",)
            ):
                status = message.subtype or "error"

    if usage is not None and num_turns is not None:
        usage = {**usage, "num_turns": num_turns}

    text = result_text or "\n".join(text_parts)
    return text, session_id, usage, status, tool_calls


def run_claude_agent(
    *,
    arm: str,
    prompt: str,
    model: str,
    sqlmesh: Path,
) -> tuple[str, str | None, dict[str, Any] | None, str, int]:
    return asyncio.run(
        _run_claude_query(arm=arm, prompt=prompt, model=model, sqlmesh=sqlmesh)
    )


def run_agent(
    *,
    provider: str,
    arm: str,
    prompt: str,
    model: str,
    api_key: str,
    sqlmesh: Path,
) -> tuple[str, str | None, dict[str, Any] | None, str, int]:
    if provider == "cursor":
        return run_cursor_agent(
            arm=arm, prompt=prompt, model=model, api_key=api_key, sqlmesh=sqlmesh
        )
    if provider == "claude":
        return run_claude_agent(arm=arm, prompt=prompt, model=model, sqlmesh=sqlmesh)
    raise ValueError(f"unknown provider: {provider}")


def median_or_none(values: list[int]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _fmt_tokens(n: float | None) -> str:
    if n is None:
        return "—"
    return f"{round(n):,}"


def _fmt_ratio(ratio: float | None) -> str:
    if ratio is None:
        return "—"
    return f"{ratio:.2f}x"


def _fmt_tools(n: float | None) -> str:
    if n is None:
        return "—"
    return str(round(n))


def _arm_stats(rows: list[dict[str, Any]], task_id: str, arm: str) -> dict[str, Any]:
    arm_rows = [r for r in rows if r["task_id"] == task_id and r["arm"] == arm]
    passes = [r for r in arm_rows if r["passed"]]
    pass_totals = [
        r["usage"]["total_tokens"]
        for r in passes
        if r.get("usage") and r["usage"].get("total_tokens") is not None
    ]
    all_totals = [
        r["usage"]["total_tokens"]
        for r in arm_rows
        if r.get("usage") and r["usage"].get("total_tokens") is not None
    ]
    pass_cache = [
        r["usage"]["cache_read_tokens"]
        for r in passes
        if r.get("usage") and r["usage"].get("cache_read_tokens") is not None
    ]
    pass_tools = [
        int(r["tool_calls"]) for r in passes if r.get("tool_calls") is not None
    ]
    all_tools = [
        int(r["tool_calls"]) for r in arm_rows if r.get("tool_calls") is not None
    ]
    return {
        "n": len(arm_rows),
        "passes": len(passes),
        "median_pass": median_or_none(pass_totals),
        "median_all": median_or_none(all_totals),
        "median_cache_pass": median_or_none(pass_cache),
        "median_tools_pass": median_or_none(pass_tools),
        "median_tools_all": median_or_none(all_tools),
    }


def summarize(rows: list[dict[str, Any]]) -> str:
    task_ids = sorted({r["task_id"] for r in rows})
    cols = ("task", "baseline", "codeparse", "ratio")
    widths = {c: len(c) for c in cols}
    table: list[dict[str, str]] = []
    overall_pass: dict[str, list[int]] = {"baseline": [], "codeparse": []}
    overall_tools: dict[str, list[int]] = {"baseline": [], "codeparse": []}

    for task_id in task_ids:
        base = _arm_stats(rows, task_id, "baseline")
        treat = _arm_stats(rows, task_id, "codeparse")
        for arm, stats in (("baseline", base), ("codeparse", treat)):
            if stats["median_pass"] is not None:
                overall_pass[arm].append(int(stats["median_pass"]))
            if stats["median_tools_pass"] is not None:
                overall_tools[arm].append(int(stats["median_tools_pass"]))

        def cell(stats: dict[str, Any]) -> str:
            score = f"{stats['passes']}/{stats['n']} pass"
            tools = _fmt_tools(
                stats["median_tools_pass"]
                if stats["median_pass"] is not None
                else stats["median_tools_all"]
            )
            if stats["median_pass"] is not None:
                tokens = _fmt_tokens(stats["median_pass"])
                cache = _fmt_tokens(stats["median_cache_pass"])
                return f"{score}  {tokens} tokens  (cache {cache}; {tools} tools)"
            tokens = _fmt_tokens(stats["median_all"])
            return f"{score}  {tokens} tokens*  ({tools} tools)"

        ratio = None
        if base["median_pass"] and treat["median_pass"]:
            ratio = treat["median_pass"] / base["median_pass"]

        row = {
            "task": task_id,
            "baseline": cell(base),
            "codeparse": cell(treat),
            "ratio": _fmt_ratio(ratio),
        }
        table.append(row)
        for c in cols:
            widths[c] = max(widths[c], len(row[c]))

    lines: list[str] = [
        "Summary",
        "=======",
        "  ".join(c.ljust(widths[c]) for c in cols),
        "  ".join("-" * widths[c] for c in cols),
    ]
    for row in table:
        lines.append("  ".join(row[c].ljust(widths[c]) for c in cols))

    base_all = median_or_none(overall_pass["baseline"])
    treat_all = median_or_none(overall_pass["codeparse"])
    ratio_all = (treat_all / base_all) if base_all and treat_all else None
    base_tools = median_or_none(overall_tools["baseline"])
    treat_tools = median_or_none(overall_tools["codeparse"])
    tools_ratio = (treat_tools / base_tools) if base_tools and treat_tools else None
    lines.extend(
        [
            "",
            "Overall (median of per-task passing medians)",
            f"  baseline : {_fmt_tokens(base_all)} tokens  ({_fmt_tools(base_tools)} tools)",
            f"  codeparse: {_fmt_tokens(treat_all)} tokens  ({_fmt_tools(treat_tools)} tools)",
            f"  ratio    : {_fmt_ratio(ratio_all)} tokens  {_fmt_ratio(tools_ratio)} tools  (codeparse / baseline)",
            "  * token medians marked with * include failed runs (no passes yet)",
        ]
    )
    return "\n".join(lines) + "\n"


def select_tasks(
    catalog: dict[str, Any],
    *,
    task_ids: list[str] | None,
) -> list[dict[str, Any]]:
    tasks = catalog["tasks"]
    if task_ids:
        wanted = set(task_ids)
        selected = [t for t in tasks if t["id"] in wanted]
        missing = wanted - {t["id"] for t in selected}
        if missing:
            raise SystemExit(f"unknown task ids: {sorted(missing)}")
        return selected
    return tasks


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("cursor", "claude"),
        default="cursor",
        help="Agent runtime (default: cursor)",
    )
    parser.add_argument(
        "--smoke", action="store_true", help="All tasks, one repeat each"
    )
    parser.add_argument("--tasks", nargs="+", help="Task ids to run")
    parser.add_argument(
        "--repeats", type=int, default=10, help="Repeats per arm (default 10)"
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model id (default: grok-4.7 for cursor, claude-opus-5-5-medium for claude)"
        ),
    )
    return parser.parse_args(argv)


def _require_api_key(provider: str) -> str:
    if provider == "cursor":
        key = os.environ.get("CURSOR_API_KEY", "").strip()
        if not key:
            print(
                "CURSOR_API_KEY is required (set it in .env or the environment)",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return key
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        print(
            "ANTHROPIC_API_KEY is required (set it in .env or the environment)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return key


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv()
    provider = args.provider
    model = args.model or DEFAULT_MODELS[provider]
    api_key = _require_api_key(provider)

    catalog = _load_tasks()
    sqlmesh = ensure_sqlmesh(catalog["sha"], catalog["repo"])
    tasks = select_tasks(catalog, task_ids=args.tasks)
    repeats = 1 if args.smoke else args.repeats
    arms = ("baseline", "codeparse")

    index_sqlmesh(sqlmesh)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"{stamp}.jsonl"
    rows: list[dict[str, Any]] = []

    print(f"provider={provider} model={model}")

    with out_path.open("w", encoding="utf-8") as fh:
        for task in tasks:
            for arm in arms:
                for repeat in range(repeats):
                    prompt = build_prompt(task, arm=arm)
                    print(
                        f"RUN {task['id']} provider={provider} "
                        f"arm={arm} repeat={repeat}"
                    )
                    try:
                        text, run_id, usage, status, tool_calls = run_agent(
                            provider=provider,
                            arm=arm,
                            prompt=prompt,
                            model=model,
                            api_key=api_key,
                            sqlmesh=sqlmesh,
                        )
                    except Exception as exc:  # noqa: BLE001 — keep going
                        text, run_id, usage, status, tool_calls = (
                            "",
                            None,
                            None,
                            f"error:{exc}",
                            None,
                        )
                    passed, missing = grade(
                        text,
                        task.get("must_contain", []),
                        task.get("must_contain_any"),
                    )
                    row = {
                        "provider": provider,
                        "task_id": task["id"],
                        "arm": arm,
                        "repeat": repeat,
                        "passed": passed,
                        "missing": missing,
                        "status": status,
                        "run_id": run_id,
                        "usage": usage,
                        "tool_calls": tool_calls,
                        "answer": text,
                        "model": model,
                        "sqlmesh_sha": catalog["sha"],
                    }
                    fh.write(json.dumps(row) + "\n")
                    fh.flush()
                    rows.append(row)
                    print(
                        f"  status={status} passed={passed} "
                        f"total={None if not usage else usage.get('total_tokens')} "
                        f"tools={tool_calls} "
                        f"missing={missing}"
                    )

    print(f"\nWrote {out_path}")
    summary = summarize(rows)
    summary_path = out_path.with_suffix(".summary.txt")
    summary_path.write_text(summary, encoding="utf-8")
    print(f"Wrote {summary_path}")
    print()
    print(summary, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
