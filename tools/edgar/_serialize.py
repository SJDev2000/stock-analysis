"""
Serialization utilities — Minimize token usage in tool outputs.

Rules:
    1. Strip None/null values from dicts (saves ~40% tokens)
    2. Round large floats to reduce decimal noise
    3. Use compact JSON (no indent)
"""

import json
from typing import Any, Dict


def strip_nulls(obj: Any) -> Any:
    """Recursively remove None values from dicts and lists."""
    if isinstance(obj, dict):
        return {k: strip_nulls(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [strip_nulls(item) for item in obj]
    return obj


def to_json(data: Dict[str, Any]) -> str:
    """Compact JSON with nulls stripped — optimized for LLM context."""
    return json.dumps(strip_nulls(data), default=str, separators=(",", ":"))


def tool_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Wrap data as MCP tool response with minimal tokens."""
    return {"content": [{"type": "text", "text": to_json(data)}]}


def tool_error(error: str, **extra) -> Dict[str, Any]:
    """Wrap error as MCP tool response."""
    payload = {"success": False, "error": error, **extra}
    return {"content": [{"type": "text", "text": to_json(payload)}], "is_error": True}
