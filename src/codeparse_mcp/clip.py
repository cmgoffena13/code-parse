"""Shared output clipping for MCP tools."""

MAX_TOOL_OUTPUT = 100_000


def clip(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    text = str(text)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"
