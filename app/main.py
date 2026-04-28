from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from app.logging_config import logger
from app.tools import (
    audit_tools,
    calls_tools,
    devices_tools,
    incidents_tools,
    meetings_tools,
    messages_tools,
    policies_tools,
    teams_tools,
    users_tools,
    voice_tools,
)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    logger.info("server_starting", transport=os.getenv("FASTMCP_TRANSPORT", "http"))
    yield
    from app.graph.client import _http_client
    await _http_client.aclose()
    logger.info("server_stopped")


mcp = FastMCP("teams-admin-support-mcp", lifespan=_lifespan)

users_tools._register(mcp)
teams_tools._register(mcp)
policies_tools._register(mcp)
calls_tools._register(mcp)
messages_tools._register(mcp)
meetings_tools._register(mcp)
devices_tools._register(mcp)
voice_tools._register(mcp)
incidents_tools._register(mcp)
audit_tools._register(mcp)


def main() -> None:
    transport = os.getenv("FASTMCP_TRANSPORT", "http")
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))
    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
