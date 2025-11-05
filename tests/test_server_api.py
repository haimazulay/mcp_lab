# tests/test_server_api.py
import os
import requests

BASE_URL = os.environ.get("MCP_BASE_URL", "http://127.0.0.1:5000")

def _post(name, arguments):
    r = requests.post(f"{BASE_URL}/call", json={"name": name, "arguments": arguments}, timeout=120)
    r.raise_for_status()
    data = r.json()
    assert data.get("ok") is True, f"{name} failed: {data}"
    return data

def test_tools_contains_all():
    r = requests.get(f"{BASE_URL}/tools", timeout=10)
    r.raise_for_status()
    tools = {t["name"] for t in r.json().get("tools", [])}
    for expected in ("now", "weather", "ask_llm"):
        assert expected in tools

def test_now_returns_iso_utc():
    data = _post("now", {})
    text = data["content"][0]["text"]
    assert text.endswith("Z") and "T" in text

def test_weather_tel_aviv():
    data = _post("weather", {"city": "Tel Aviv"})
    j = data["content"][0]["json"]
    assert "coords" in j and "current_weather" in j

def test_ask_llm_mcp_semantics():
    data = _post("ask_llm", {"prompt": "Explain MCP in one sentence."})
    text = data["content"][0]["text"].lower()
    assert "model context protocol" in text
    assert "microsoft certified" not in text
