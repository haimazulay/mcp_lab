# agent_demo.py
import asyncio
import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


def parse_args() -> argparse.Namespace:
    """Simple CLI for choosing which server/tools to run."""
    p = argparse.ArgumentParser(description="MCP Agent Demo")
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
        help="Specific tool to call (if omitted: runs the lab flow for 'demo', or system_info for 'system')",
    )
    p.add_argument("--city", default="Tel Aviv", help="City for weather")
    return p.parse_args()


def pick_server_path(which: str) -> str:
    fname = "mcp_server_demo.py" if which == "demo" else "mcp_server_system.py"
    return str(Path(__file__).with_name(fname))


async def run_lab_flow_demo(session: ClientSession) -> None:
    """Run the exact Expected Output flow from the lab (now + weather(Tel Aviv))."""
    # Tools header
    print("--- Tools available ---")
    print("- now: Returns the current server time in ISO 8601 (UTC).")
    print("- weather: Get current weather for a city using Open-Meteo (no API key).")
    print()

    # Task 1
    print("== Task 1: What time is it right now? Return ISO time.")
    now_res = await asyncio.wait_for(session.call_tool("now", {}), timeout=15)
    iso_text = next((getattr(c, "text", None) for c in now_res.content if getattr(c, "type", "") == "text"), None)
    print(iso_text or "(no time)")
    print()

    # Task 2
    print("== Task 2: What's the current weather in Tel Aviv?")
    w_res = await asyncio.wait_for(session.call_tool("weather", {"city": "Tel Aviv"}), timeout=30)

    # Extract JSON (prefer json content; fallback: parse text as JSON)
    data: Optional[Dict[str, Any]] = None
    for c in w_res.content:
        t = getattr(c, "type", "")
        if t == "json":
            import json
            json_content = c.json()
            if isinstance(json_content, str):
                try:
                    data = json.loads(json_content)
                except Exception:
                    data = None
            else:
                data = json_content
            break
        if t == "text" and hasattr(c, "text"):
            import json
            try:
                data = json.loads(getattr(c, "text", ""))
            except Exception:
                data = None
            break

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


async def main() -> None:
    args = parse_args()
    server_path = pick_server_path(args.server)

    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", server_path],  # unbuffered stdio (critical on Windows)
        cwd=str(Path(__file__).parent),
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            # Handshake + tools
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}

            # If user didn't specify a tool:
            if args.tool is None:
                if args.server == "demo":
                    # Run the lab's expected flow
                    await run_lab_flow_demo(session)
                    return
                else:
                    # system server → default to system_info
                    args.tool = "system_info"

            # Dispatch single tool
            if args.tool == "now":
                if "now" not in names:
                    raise RuntimeError("Server does not expose 'now'")
                res = await asyncio.wait_for(session.call_tool("now", {}), timeout=15)
                print(res)

            elif args.tool == "weather":
                if "weather" not in names:
                    raise RuntimeError("Server does not expose 'weather'")
                res = await asyncio.wait_for(
                    session.call_tool("weather", {"city": args.city}), timeout=30
                )
                print(res)

            elif args.tool == "system_info":
                if "system_info" not in names:
                    raise RuntimeError("Server does not expose 'system_info'")
                res = await asyncio.wait_for(session.call_tool("system_info", {}), timeout=10)
                print(res)


if __name__ == "__main__":
    asyncio.run(main())
