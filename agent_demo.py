#!/usr/bin/env python3
# agent_demo.py
import asyncio
import os
import sys
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# ---------- CLI args ----------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MCP Agent Demo (stdio)")
    p.add_argument(
        "--server",
        choices=["demo", "system"],
        default="demo",
        help="Which MCP server to launch (demo: now/weather, system: system_info)",
    )
    p.add_argument(
        "--tool",
        choices=["now", "weather", "system_info"],
        default=None,
        help="Specific tool to call (if omitted: runs lab flow for 'demo', or system_info for 'system')",
    )
    p.add_argument("--city", default="Tel Aviv", help="City for weather tool")
    return p.parse_args()

# ---------- resolve server path ----------
def pick_server_path(which: str) -> str:
    fname = "mcp_server_demo.py" if which == "demo" else "mcp_server_system.py"
    return str(Path(__file__).with_name(fname))

# ---------- response helpers ----------
def _extract_text(resp) -> Optional[str]:
    """Return first text block from a ToolResponse (or None)."""
    for c in getattr(resp, "content", []) or []:
        if getattr(c, "type", None) == "text":
            return getattr(c, "text", None)
    return None

def _extract_json(resp) -> Optional[Dict[str, Any]]:
    """Return dict from a ToolResponse (json block or JSON text)."""
    for c in getattr(resp, "content", []) or []:
        ctype = getattr(c, "type", None)
        if ctype == "json":
            val = getattr(c, "json", None)
            return val if isinstance(val, dict) else None
        if ctype == "text":
            try:
                txt = getattr(c, "text", "") or ""
                return json.loads(txt)
            except Exception:
                return None
    return None

# ---------- lab flow (expected output) ----------
async def run_lab_flow_demo(session: ClientSession) -> None:
    print("--- Tools available ---")
    print("- now: Returns the current server time in ISO 8601 (UTC).")
    print("- weather: Get current weather for a city using Open-Meteo (no API key).")
    print()

    # Task 1
    print("== Task 1: What time is it right now? Return ISO time.")
    now_res = await asyncio.wait_for(session.call_tool("now", arguments={}), timeout=15)
    iso_text = _extract_text(now_res)
    print(iso_text or "(no time)")
    print()

    # Task 2
    print("== Task 2: What's the current weather in Tel Aviv?")
    w_res = await asyncio.wait_for(
        session.call_tool("weather", arguments={"city": "Tel Aviv"}), timeout=30
    )
    data = _extract_json(w_res)
    if data and "current_weather" in data:
        cw = data["current_weather"] or {}
        temp = cw.get("temperature")
        wind = cw.get("windspeed")
        if temp is not None and wind is not None:
            print(f"The current weather in Tel Aviv is {temp}°C, windspeed {wind} km/h.")
        else:
            print("Weather data available but missing fields.")
    else:
        print("Could not retrieve weather.")

# ---------- main ----------
async def main() -> None:
    args = parse_args()
    server_path = pick_server_path(args.server)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", server_path],  # unbuffered stdio (Windows-safe)
        cwd=str(Path(__file__).parent),
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the MCP protocol handshake
            await session.initialize()

            # List tools (also ensures server is ready)
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}

            # Default lab flow
            if args.tool is None and args.server == "demo":
                await run_lab_flow_demo(session)
                return

            # Dispatch to explicit or sensible default tool
            tool = args.tool or ("system_info" if args.server == "system" else "now")

            if tool == "now":
                if "now" not in names:
                    raise RuntimeError("Server does not expose 'now'")
                res = await asyncio.wait_for(session.call_tool("now", arguments={}), timeout=15)
                print(res)

            elif tool == "weather":
                if "weather" not in names:
                    raise RuntimeError("Server does not expose 'weather'")
                res = await asyncio.wait_for(
                    session.call_tool("weather", arguments={"city": args.city}), timeout=30
                )
                print(res)

            elif tool == "system_info":
                if "system_info" not in names:
                    raise RuntimeError("Server does not expose 'system_info'")
                res = await asyncio.wait_for(session.call_tool("system_info", arguments={}), timeout=10)
                data = _extract_json(res)
                if isinstance(data, dict):
                    print(f"Username: {data.get('username')} | OS: {data.get('os')} | Version: {data.get('version')}")
                else:
                    print(res)

if __name__ == "__main__":
    asyncio.run(main())
