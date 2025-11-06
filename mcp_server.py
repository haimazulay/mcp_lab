# mcp_server.py
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP


# --- Safe logging (stderr only) ---
def log(msg: str) -> None:
    """Log safely to stderr so we don't corrupt MCP stdout."""
    print(f"[server] {msg}", file=sys.stderr, flush=True)


# --- Initialize MCP server ---
mcp = FastMCP("mcp-lab")
log("server boot")


# --- now ---
@mcp.tool()
def now() -> str:
    """Return the current UTC time in ISO-8601 format."""
    log("now() called")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# --- weather (Open-Meteo) ---
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

@mcp.tool()
async def weather(city: str) -> Dict[str, Any]:
    """Get current weather for a city using Open-Meteo API."""
    log(f"weather(city={city!r}) called")
    async with httpx.AsyncClient(timeout=30.0) as client:
        g = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        g.raise_for_status()
        results = g.json().get("results") or []

        if not results:
            return {"error": f"City not found: {city}"}

        top = results[0]
        lat, lon = top["latitude"], top["longitude"]

        f = await client.get(
            FORECAST_URL,
            params={"latitude": lat, "longitude": lon, "current_weather": True},
        )
        f.raise_for_status()
        cw = f.json().get("current_weather")

        return {
            "city": top["name"],
            "country": top.get("country", ""),
            "coords": {"lat": lat, "lon": lon},
            "current_weather": cw,
        }


# --- ask_llm (Ollama) ---
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_SYSTEM = (
    "You are an AI assistant working on the Model Context Protocol (MCP) project by OpenAI. "
    "Here, 'MCP' always means the Model Context Protocol, never Microsoft certifications."
)

@mcp.tool()
async def ask_llm(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    top_p: float = 0.9,
    system: Optional[str] = None,
) -> str:
    """Send a prompt to a local LLM via Ollama."""
    log("ask_llm() called")

    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system or DEFAULT_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "top_p": top_p},
    }

    # Short timeout to avoid hanging when Ollama isn't running.
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        return (data.get("message") or {}).get("content") or ""
    except httpx.HTTPStatusError as exc:
        return f"error: ollama HTTP {exc.response.status_code} ({exc})"
    except httpx.RequestError as exc:
        return f"error: ollama unavailable ({exc})"


# --- Entry point ---
if __name__ == "__main__":
    mcp.run()
