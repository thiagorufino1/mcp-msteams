from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastmcp import FastMCP

from mcp_msteams.graph.client import _http_client
from mcp_msteams.logging_config import logger
from mcp_msteams.tools import (
    calls_tools,
    incidents_tools,
    meetings_tools,
    reports_tools,
    teams_tools,
    users_tools,
)


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    logger.info("server_starting", transport=os.getenv("FASTMCP_TRANSPORT", "http"))
    yield
    try:
        await _http_client.aclose()
    except Exception:
        pass
    logger.info("server_stopped")


mcp = FastMCP("teams-admin-support-mcp", lifespan=_lifespan)

users_tools._register(mcp)
teams_tools._register(mcp)
calls_tools._register(mcp)
meetings_tools._register(mcp)
reports_tools._register(mcp)
incidents_tools._register(mcp)


def main() -> None:
    transport = os.getenv("FASTMCP_TRANSPORT", "http")
    host = os.getenv("FASTMCP_HOST", "127.0.0.1")
    port = int(os.getenv("FASTMCP_PORT", "8000"))
    mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
