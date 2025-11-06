# tests/test_mcp_demo.py
import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


PROJECT_DIR = Path(__file__).resolve().parents[1]


async def _list_tools_for(server_file: str):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(PROJECT_DIR / server_file)],
        cwd=str(PROJECT_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            out = await session.list_tools()
            return {t.name for t in out.tools}


@pytest.mark.asyncio
async def test_demo_server_tools():
    names = await _list_tools_for("mcp_server_demo.py")
    assert "now" in names
    assert "weather" in names


@pytest.mark.asyncio
async def test_system_server_tools():
    names = await _list_tools_for("mcp_server_system.py")
    assert "system_info" in names
