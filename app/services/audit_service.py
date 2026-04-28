from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.config import settings

_buffer: deque[dict[str, Any]] = deque(maxlen=settings.audit_buffer_size)
_lock = threading.Lock()


def record(
    *,
    tool: str,
    upn_hint: str,
    elapsed_ms: int,
    status: str,
    error_type: str | None,
) -> None:
    entry: dict[str, Any] = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "tool": tool,
        "upn_hint": upn_hint,
        "elapsed_ms": elapsed_ms,
        "status": status,
        "error_type": error_type,
    }
    with _lock:
        _buffer.append(entry)


def get_history(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        entries = list(_buffer)
    return entries[-limit:]


def get_summary() -> dict[str, Any]:
    with _lock:
        entries = list(_buffer)
    total = len(entries)
    if total == 0:
        return {"total_calls": 0, "message": "No tool calls recorded yet."}
    errors = sum(1 for e in entries if e["status"] == "error")
    tools_used = sorted({e["tool"] for e in entries})
    avg_elapsed = sum(e["elapsed_ms"] for e in entries) / total
    return {
        "total_calls": total,
        "error_count": errors,
        "success_rate": f"{(total - errors) / total * 100:.1f}%",
        "avg_elapsed_ms": round(avg_elapsed),
        "tools_used": tools_used,
        "recent": entries[-10:],
    }


def get_by_upn(upn_hint: str, limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        entries = list(_buffer)
    matched = [e for e in entries if upn_hint.lower() in e.get("upn_hint", "").lower()]
    return matched[-limit:]
