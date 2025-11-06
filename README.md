# 🧩 MCP Lab

A minimal **Model Context Protocol (MCP)** lab demonstrating:

- Real stdio-based MCP servers (`mcp_server_demo.py`, `mcp_server_system.py`)  
- A lightweight HTTP bridge (`app_http_bridge.py`) for web access  
- A simple HTML/JS frontend  
- An async Python agent/CLI  

Everything runs **locally**, no external API keys required.

---

## 📦 What’s Included

### 🧠 MCP Servers
| File | Description | Tools |
|------|--------------|--------|
| `mcp_server_demo.py` | Main demo server | `now` (current UTC time) • `weather(city)` (via Open-Meteo) |
| `mcp_server_system.py` | “Do You Know Who I Am?” exercise | `system_info` (username, OS, version) |

Each server uses the official [`mcp`](https://pypi.org/project/mcp/) library and communicates via **stdio**.

---

### 🌉 HTTP Bridge
| File | Description |
|------|--------------|
| `app_http_bridge.py` | Flask bridge exposing `/tools` and `/call` endpoints, internally spawning MCP servers for each request. Enables browser access with CORS. |

Endpoints:
- `GET /tools?server=demo|system` → list tools  
- `POST /call` → execute tool (`{"name":"now","arguments":{},"server":"demo"}`)

---

### 💻 Frontend (Vanilla HTML/JS)
| File | Description |
|------|--------------|
| `index.html` | Web UI (RTL Hebrew layout) that calls the bridge endpoints. Includes buttons for `now`, `weather`, and `system_info`. |

---

### 🐍 CLI / Agent
| File | Description |
|------|--------------|
| `agent_demo.py` | Async Python client that connects to the MCP server via stdio, lists tools, and performs the lab flow exactly as described in the exercise. |

---

## ⚙️ Requirements

- Python **3.10+**
- `pip` (latest)
- Internet connection (for the weather API)

---

## 🚀 Quick Start

### 1️⃣ Create & Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.env\Scripts\Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2️⃣ Install Dependencies
```bash
pip install flask flask-cors mcp httpx
```

### 3️⃣ Run the HTTP Bridge
```bash
python app_http_bridge.py
```
Bridge runs at **http://127.0.0.1:5000**

You should see something like:
```
[bridge] launch: python -u mcp_server_demo.py ...
```

---

### 4️⃣ Test Endpoints (PowerShell)
```powershell
# Health
irm "http://127.0.0.1:5000/"

# List tools (demo server)
irm "http://127.0.0.1:5000/tools?server=demo" | ConvertTo-Json -Depth 5

# Call tool: now
$body = '{"name":"now","arguments":{},"server":"demo"}'
irm "http://127.0.0.1:5000/call" -Method Post -ContentType 'application/json' -Body $body | ConvertTo-Json -Depth 5
```

Expected output:
```json
{
  "ok": true,
  "server": "demo",
  "tool": "now",
  "content": [
    { "type": "text", "text": "2025-11-06T21:32:30.548Z" }
  ]
}
```

---

### 5️⃣ Run the Web UI
```bash
# In another terminal
python -m http.server 5500
```
Then open **http://127.0.0.1:5500/index.html**

> Make sure `app_http_bridge.py` is running in the background.

---

### 6️⃣ Run the MCP Agent (stdio)
```bash
python agent_demo.py
```

Expected output:
```
--- Tools available ---
- now: Returns the current server time in ISO 8601 (UTC).
- weather: Get current weather for a city using Open-Meteo (no API key).

== Task 1: What time is it right now? Return ISO time.
2025-11-06T21:32:30.548Z

== Task 2: What's the current weather in Tel Aviv?
The current weather in Tel Aviv is 24°C, windspeed 6 km/h.
```

---

## 🧠 Notes

- MCP servers communicate strictly over **stdio**, not HTTP.  
  The Flask bridge only translates between HTTP (for browsers) and stdio (for MCP).
- All logging inside MCP servers goes to **stderr** only (stdout is reserved for protocol JSON).
- The `weather` tool uses the [Open-Meteo API](https://open-meteo.com/) (no API key required).
- The project structure follows the **“MCP Server Demo — First-Time Lab”** exercise specification.

---

## 🧪 Optional Enhancements

- Add an Ollama-powered `ask_llm` tool for model-driven tool invocation.  
- Implement persistent MCP sessions in the bridge for faster responses.  
- Extend the Web UI to auto-discover tools dynamically from `/tools`.

---

## 🖼️ Architecture Overview

```
Browser (index.html)
        │
        ▼
HTTP (CORS)
        │
        ▼
Flask Bridge ───▶ MCP Server (stdio)
   /tools, /call        ├── now()
                        ├── weather(city)
                        └── system_info()
```

---

© 2025 — MCP Lab Educational Project
