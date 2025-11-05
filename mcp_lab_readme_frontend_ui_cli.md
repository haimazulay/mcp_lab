# MCP Lab

A minimal MCP-style toolkit demonstrating a local Flask server that exposes tools, a simple web UI, and a Python CLI.

---

## What’s Included

* **Server (Flask)** — `/tools` for tool metadata and `/call` to execute tools.
* **Tools**

  * `now` — returns current UTC time (ISO-8601).
  * `weather` — current weather by city via Open‑Meteo.
  * `ask_llm` — prompts a local LLM through Ollama (with a steering system prompt).
* **Frontend (Vanilla HTML/JS)** — buttons to call each tool (CORS enabled).
* **Client (Python)** — async client and an interactive CLI.
* **Tests (optional)** — smoke tests for all tools with `pytest`.

---

## Requirements

* Python 3.10+
* pip (updated)
* Ollama (running locally)

> Models: tested with `llama3.2:3b`.

---

## Quick Start

### 1) Create & Activate venv

```bash
# Windows (PowerShell)
python -m venv venv
./venv/Scripts/Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 2) Install Dependencies

```bash
pip install -r requirements.txt
```

### 3) Prepare Ollama

```bash
ollama --version
ollama pull llama3.2:3b
```

### 4) Run the Server

```bash
python -m server.app
```

Server runs at: `http://127.0.0.1:5000`

### 5) Run the Web UI

```bash
cd web
python -m http.server 5500
```

Open: `http://127.0.0.1:5500` and use the buttons.

### 6) Run the CLI

```bash
python -m client.cli
```

### 7) (Optional) Run Tests

```bash
pytest -q
```

---

## Notes

* CORS is enabled for development so the web UI can call the server.
* `ask_llm` uses a default system prompt to interpret “MCP” as **Model Context Protocol**.
* The project is designed for local use and easy extension with new tools.
