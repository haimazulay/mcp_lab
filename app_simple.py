# app_simple.py - Flask server WITHOUT MCP stdio (for debugging)
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from flask_cors import CORS
import httpx
import platform
import getpass

app = Flask(__name__)
CORS(app)

# ============== TOOLS IMPLEMENTED DIRECTLY ==============

def tool_now():
    """Return current UTC time."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def tool_system_info():
    """Return system info."""
    return {
        "username": getpass.getuser(),
        "os": platform.system(),
        "version": platform.version(),
    }

async def tool_weather(city: str):
    """Get weather from Open-Meteo."""
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Geocode
        g = await client.get(GEOCODE_URL, params={"name": city, "count": 1})
        g.raise_for_status()
        results = g.json().get("results") or []
        
        if not results:
            return {"error": f"City not found: {city}"}
        
        top = results[0]
        lat, lon = top["latitude"], top["longitude"]
        
        # Weather
        f = await client.get(
            FORECAST_URL,
            params={"latitude": lat, "longitude": lon, "current_weather": True},
        )
        f.raise_for_status()
        
        return {
            "city": top.get("name", city),
            "country": top.get("country", ""),
            "coords": {"lat": lat, "lon": lon},
            "current_weather": f.json().get("current_weather"),
        }

# ============== ROUTES ==============

@app.get("/")
def health():
    return jsonify({"status": "running", "message": "Simple MCP Server (No stdio)"})

@app.get("/tools")
def get_tools():
    """List available tools."""
    tools = [
        {
            "name": "now",
            "description": "Returns current UTC time in ISO 8601 format",
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "weather",
            "description": "Get current weather for a city",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"}
                },
                "required": ["city"]
            }
        },
        {
            "name": "system_info",
            "description": "Get local system information",
            "inputSchema": {"type": "object", "properties": {}}
        }
    ]
    return jsonify({"ok": True, "tools": tools})

@app.post("/call")
def call_tool():
    """Call a tool."""
    data = request.get_json(force=True) or {}
    name = data.get("name")
    args = data.get("arguments") or {}
    
    if not name:
        return jsonify({"ok": False, "error": "Missing 'name' field"}), 400
    
    try:
        # Dispatch
        if name == "now":
            result = tool_now()
            return jsonify({
                "ok": True,
                "tool": name,
                "content": [{"type": "text", "text": result}]
            })
        
        elif name == "system_info":
            result = tool_system_info()
            return jsonify({
                "ok": True,
                "tool": name,
                "content": [{"type": "json", "json": result}]
            })
        
        elif name == "weather":
            city = args.get("city", "Tel Aviv")
            # Run async function
            import asyncio
            result = asyncio.run(tool_weather(city))
            return jsonify({
                "ok": True,
                "tool": name,
                "content": [{"type": "json", "json": result}]
            })
        
        else:
            return jsonify({"ok": False, "error": f"Unknown tool: {name}"}), 404
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"ok": False, "error": str(e)}), 500

# ============== MAIN ==============

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Simple Flask MCP Server (No stdio)")
    print("   Tools: now, weather, system_info")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)