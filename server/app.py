from flask import Flask, jsonify, request
from flask_cors import CORS

try:
    from tools.now import get_now_iso_utc
    from tools.weather import get_weather_for_city, WeatherError
    from tools.llm import  ask_llm_chat,LLMError
except ImportError:
    from .tools.now import get_now_iso_utc
    from .tools.weather import get_weather_for_city, WeatherError
    from .tools.llm import  ask_llm_chat,LLMError

import asyncio

app = Flask(__name__)
CORS(app)
# --- Minimal "MCP-like" HTTP surface ---
# Endpoints:
# 1) GET /tools  -> list available tools (metadata)
# 2) POST /call  -> execute a tool by name with arguments

@app.get("/tools")
def list_tools():
    return jsonify({
        "tools": [
            {
                "name": "now",
                "description": "Get the current UTC time in ISO-8601 format.",
                "input_schema": {"type": "object", "properties": {}, "required": []}
            },
            {
                "name": "weather",
                "description": "Get current weather for a city using Open-Meteo.",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"]
                }
            },
            {
                "name": "ask_llm",
                "description": "Send a prompt to a local LLM via Ollama and get a response.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "model":  {"type": "string"},
                        "temperature": {"type": "number"},
                        "system": {"type": "string"},
                        "top_p": {"type": "number"}
                    },
                    "required": ["prompt"]
                }
            }
        ]
    })

@app.post("/call")
def call_tool():
    """Execute a tool by name with given arguments (JSON)."""
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    args = data.get("arguments", {}) or {}

    # Tool: now
    if name == "now":
        iso = get_now_iso_utc()
        return jsonify({"ok": True, "content": [{"type": "text", "text": iso}]})

    if name == "ask_llm":
        prompt = args.get("prompt")
        model = args.get("model")
        temperature = args.get("temperature")
        system = args.get("system")
        top_p = args.get("top_p")
        if not prompt or not isinstance(prompt, str):
            return jsonify({"ok": False, "error": "Prompt parameter must be a non-empty string"}), 400
        try:
            text = asyncio.run(
                ask_llm_chat(
                    prompt=prompt,
                    model=model,
                    system=system,  # if None -> uses DEFAULT_SYSTEM
                    temperature=temperature if isinstance(temperature, (int, float)) else 0.1,
                    top_p=top_p if isinstance(top_p, (int, float)) else 0.9,
                )
            )
            return jsonify({"ok": True, "content": [{"type": "text", "text": text}]})
        except LLMError as le:
            return jsonify({"ok": False, "error": str(le)}), 400
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500

    # Tool: weather
    if name == "weather":
        city = args.get("city")
        if not city or not isinstance(city, str):
            return jsonify({"ok": False, "error": "City parameter must be a non-empty string"}), 400
        try:
            result = asyncio.run(get_weather_for_city(city))
            return jsonify({"ok": True, "content": [{"type": "json", "json": result}]})
        except WeatherError as we:
            return jsonify({"ok": False, "error": str(we)}), 400
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500

    # Unknown tool
    return jsonify({"ok": False, "error": f"Unknown tool: {name}"}), 400


if __name__ == "__main__":
    # For local dev; in production prefer a WSGI/ASGI server.
    app.run(host="127.0.0.1", port=5000, debug=True)
