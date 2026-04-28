from __future__ import annotations

import functools
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Callable

import structlog

from app.config import settings

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")

_log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(_log_level),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger("teams_mcp")


def audited(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: injects trace_id, logs invocation/completion/failure, writes audit entry."""

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tid = uuid.uuid4().hex[:8]
        _trace_id.set(tid)
        t0 = time.monotonic()
        elapsed_ms = 0
        tool_name = fn.__name__

        from app.utils.sanitization import sanitize_log_value
        safe_kwargs = {k: sanitize_log_value(str(v)) for k, v in kwargs.items()}
        logger.info("tool_invoked", tool=tool_name, trace_id=tid, **safe_kwargs)

        try:
            result = await fn(*args, **kwargs)
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            logger.info("tool_completed", tool=tool_name, trace_id=tid, elapsed_ms=elapsed_ms)
            _record(tool_name, safe_kwargs, elapsed_ms, "ok", None)
            return result
        except Exception as exc:
            elapsed_ms = round((time.monotonic() - t0) * 1000)
            logger.error("tool_failed", tool=tool_name, trace_id=tid, elapsed_ms=elapsed_ms, error=str(exc))
            _record(tool_name, safe_kwargs, elapsed_ms, "error", type(exc).__name__)
            raise

    return wrapper


def _record(tool: str, safe_kwargs: dict[str, Any], elapsed_ms: int, status: str, error_type: str | None) -> None:
    from app.services.audit_service import record
    from app.utils.sanitization import mask_upn
    upn_hint = mask_upn(str(safe_kwargs.get("upn", safe_kwargs.get("upn1", ""))))
    record(tool=tool, upn_hint=upn_hint, elapsed_ms=elapsed_ms, status=status, error_type=error_type)
