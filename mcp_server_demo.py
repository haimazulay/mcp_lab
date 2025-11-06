#!/usr/bin/env python3
# mcp_server_demo.py
import sys
from datetime import datetime, timezone
from typing import Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP

# ---------- safe stderr logging ----------
def log(msg: str) -> None:
    """Log to stderr only; stdout is reserved for MCP protocol."""
    print(f"[server] {msg}", file=sys.stderr, flush=True)

# ---------- init ----------
mcp = FastMCP("mcp-demo")
log("server boot")

# ---------- tool: now ----------
@mcp.tool()
def now() -> str:
    """Return current UTC time in ISO 8601 (UTC)."""
    log("now() called")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# ---------- tool: weather (Open-Meteo) ----------
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

@mcp.tool()
async def weather(city: str) -> Dict[str, Any]:
    """Get current weather for a city using Open-Meteo (no API key)."""
    log(f"weather(city={city!r}) called")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1) Geocode
        g = await client.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "en"})
        g.raise_for_status()
        results = g.json().get("results") or []
        if not results:
            return {"error": f"City not found: {city}"}

        top = results[0]
        lat, lon = top["latitude"], top["longitude"]

        # 2) Current weather
        f = await client.get(
            FORECAST_URL,
            params={"latitude": lat, "longitude": lon, "current_weather": True},
        )
        f.raise_for_status()
        cw = f.json().get("current_weather") or {}

        return {
            "city": top.get("name", city),
            "country": top.get("country", ""),
            "coords": {"lat": lat, "lon": lon},
            "current_weather": cw,  # temperature (°C), windspeed (km/h), time, etc.
        }

if __name__ == "__main__":
    # Run MCP over stdio (no prints to stdout!)
    mcp.run()
