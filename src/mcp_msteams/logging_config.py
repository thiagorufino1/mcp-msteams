from __future__ import annotations

import functools
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable

import structlog

from mcp_msteams.config import settings
from mcp_msteams.utils.sanitization import sanitize_log_value

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")

_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
_log_format = settings.log_format.lower()

_renderer = (
    structlog.dev.ConsoleRenderer()
    if _log_format == "console"
    else structlog.processors.JSONRenderer()
)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        _renderer,
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger("teams_mcp")


def audited(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: injects trace_id and logs invocation/completion/failure.

    Note: this is structured execution logging, not a persistent audit trail.
    """

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tid = uuid.uuid4().hex[:8]
        _trace_id.set(tid)
        t0 = time.monotonic()
        elapsed_ms = 0
        tool_name = fn.__name__

        safe_kwargs = {k: sanitize_log_value(str(v)) for k, v in kwargs.items()}
        logger.info("tool_invoked", tool=tool_name, trace_id=tid, **safe_kwargs)

        try:
            result = await fn(*args, **kwargs)
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            status, error_type = _result_status(result)
            logger.info("tool_completed", tool=tool_name, trace_id=tid, elapsed_ms=elapsed_ms, status=status)
            return result
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            logger.error(
                "tool_failed",
                tool=tool_name,
                trace_id=tid,
                elapsed_ms=elapsed_ms,
                error=sanitize_log_value(str(exc)),
            )
            raise

    return wrapper


def _result_status(result: Any) -> tuple[str, str | None]:
    if not isinstance(result, dict):
        return ("ok", None)
    if result.get("error"):
        error_type = str(result.get("error"))
        return ("error", error_type)
    if result.get("status") == "not_implemented":
        return ("not_implemented", "not_implemented")
    return ("ok", None)
