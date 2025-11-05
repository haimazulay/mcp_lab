# MCP Lab — README, Frontend UI, and CLI

> הסברים בעברית; הקוד וההערות באנגלית בלבד.

---

## 1) התקנות (Windows / Linux / macOS)

### Prerequisites
- **Python 3.10+** (`python --version`)
- **pip** מעודכן (`python -m pip install --upgrade pip`)
- **Ollama** מותקן ורץ מקומית (Windows: התקן מהאתר הרשמי, פתח PowerShell חדש)
  - בדיקה: `ollama --version`
  - משיכת מודל לדוגמה: `ollama pull llama3.2:3b`

### Create & activate venv
```bash
# Windows (PowerShell)
python -m venv venv
./venv/Scripts/Activate.ps1

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Install Python deps
עדכן/צור `requirements.txt` כך:
```
Flask==3.0.0
httpx==0.27.2
pytest==8.3.2
requests==2.32.3
flask-cors==4.0.0
```
והתקן:
```bash
pip install -r requirements.txt
```

---

## 2) פריסת קבצים (מבנה מומלץ)
```
mcp_lab/
  server/
    app.py
    tools/
      __init__.py
      now.py
      weather.py
      llm.py
  client/
    main.py
    cli.py           # NEW — interactive CLI
  web/
    index.html       # NEW — simple frontend UI
  requirements.txt
  tests/
    test_server_api.py (optional)
```

---

## 3) עדכון השרת לאפשר CORS (כדי שה-Frontend יעבוד בדפדפן)

### server/app.py (קטע רלוונטי)
```python
from flask import Flask, jsonify, request
from flask_cors import CORS  # NEW

# Local imports with dual-mode support (module/package)
try:
    from tools.now import get_now_iso_utc
    from tools.weather import get_weather_for_city, WeatherError
    from tools.llm import ask_llm_chat, LLMError
except ImportError:
    from .tools.now import get_now_iso_utc
    from .tools.weather import get_weather_for_city, WeatherError
    from .tools.llm import ask_llm_chat, LLMError

import asyncio

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes (development only)

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
                        "model": {"type": "string"},
                        "system": {"type": "string"},
                        "temperature": {"type": "number"},
                        "top_p": {"type": "number"}
                    },
                    "required": ["prompt"]
                }
            }
        ]
    })

@app.post("/call")
def call_tool():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    args = data.get("arguments", {}) or {}

    if name == "now":
        iso = get_now_iso_utc()
        return jsonify({"ok": True, "content": [{"type": "text", "text": iso}]})

    if name == "weather":
        city = args.get("city")
        try:
            result = asyncio.run(get_weather_for_city(city))
            return jsonify({"ok": True, "content": [{"type": "json", "json": result}]})
        except WeatherError as we:
            return jsonify({"ok": False, "error": str(we)}), 400
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500

    if name == "ask_llm":
        prompt = args.get("prompt")
        model = args.get("model") or None
        system = args.get("system") or None
        temperature = args.get("temperature")
        top_p = args.get("top_p")
        try:
            text = asyncio.run(
                ask_llm_chat(
                    prompt=prompt,
                    model=model,
                    system=system,
                    temperature=temperature if isinstance(temperature, (int, float)) else 0.1,
                    top_p=top_p if isinstance(top_p, (int, float)) else 0.9,
                )
            )
            return jsonify({"ok": True, "content": [{"type": "text", "text": text}]})
        except LLMError as le:
            return jsonify({"ok": False, "error": str(le)}), 400
        except Exception as exc:
            return jsonify({"ok": False, "error": f"Unexpected error: {exc}"}), 500

    return jsonify({"ok": False, "error": f"Unknown tool: {name}"}), 400

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

> הערה: CORS פתוח מתאים לפיתוח מקומי. לפרודקשן — צמצם מקורות/כותרות לפי הצורך.

---

## 4) קבצי הכלים (Tools) — תזכורת

### server/tools/llm.py
```python
import httpx
from typing import Dict, Any, Optional

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"

# Strong system prompt to avoid confusion with Microsoft certification
DEFAULT_SYSTEM = (
    "You are an AI assistant working on the Model Context Protocol (MCP) project by OpenAI. "
    "In this project, 'MCP' always means the Model Context Protocol for AI tool integrations, "
    "never Microsoft certifications. Keep answers short and precise."
)

class LLMError(Exception):
    pass

async def ask_llm_chat(
    prompt: str,
    model: Optional[str] = None,
    base_url: str = DEFAULT_OLLAMA_URL,
    system: Optional[str] = DEFAULT_SYSTEM,
    temperature: float = 0.1,
    top_p: float = 0.9,
) -> str:
    if not prompt or not prompt.strip():
        raise LLMError("Prompt is required.")

    model = model or DEFAULT_MODEL
    system = system or DEFAULT_SYSTEM

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "top_p": top_p},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{base_url}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
        text = (data.get("message") or {}).get("content")
        if not text:
            raise LLMError("Empty response from model.")
        return text
```

> הקבצים `now.py` ו-`weather.py` נשארים כמו שבנית קודם.

---

## 5) Frontend UI (Vanilla HTML/JS)

**web/index.html**
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MCP Lab UI</title>
  <style>
    body { font-family: system-ui, Arial, sans-serif; margin: 24px; }
    h1 { margin-bottom: 8px; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 16px; margin: 12px 0; }
    label { display:block; margin: 6px 0 4px; }
    input, textarea, select, button { font-size: 16px; padding: 8px; }
    pre { background: #111; color: #eee; padding: 12px; border-radius: 8px; overflow:auto; }
    .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  </style>
</head>
<body>
  <h1>MCP Lab — Frontend UI</h1>
  <p>Call tools on your local Flask server.</p>

  <div class="card">
    <h2>Tools</h2>
    <button id="btnLoadTools">Load /tools</button>
    <pre id="toolsOut">(no data)</pre>
  </div>

  <div class="card">
    <h2>now</h2>
    <button id="btnNow">Call now</button>
    <pre id="nowOut">(no data)</pre>
  </div>

  <div class="card">
    <h2>weather</h2>
    <label for="city">City</label>
    <input id="city" placeholder="Tel Aviv" value="Tel Aviv" />
    <div class="row">
      <button id="btnWeather">Call weather</button>
    </div>
    <pre id="weatherOut">(no data)</pre>
  </div>

  <div class="card">
    <h2>ask_llm</h2>
    <label for="prompt">Prompt</label>
    <textarea id="prompt" rows="3" placeholder="Explain MCP in one sentence.">Explain MCP in one sentence.</textarea>

    <label for="model">Model (optional)</label>
    <input id="model" placeholder="llama3.2:3b" />

    <div class="row">
      <button id="btnAsk">Call ask_llm</button>
    </div>
    <pre id="askOut">(no data)</pre>
  </div>

  <script>
    const BASE = 'http://127.0.0.1:5000';

    async function getJSON(url) {
      const r = await fetch(url);
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }

    async function postJSON(url, body) {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      if (!r.ok) {
        const text = await r.text();
        throw new Error('HTTP ' + r.status + ': ' + text);
      }
      return r.json();
    }

    document.getElementById('btnLoadTools').onclick = async () => {
      try {
        const data = await getJSON(`${BASE}/tools`);
        toolsOut.textContent = JSON.stringify(data, null, 2);
      } catch (err) { toolsOut.textContent = String(err); }
    };

    document.getElementById('btnNow').onclick = async () => {
      try {
        const data = await postJSON(`${BASE}/call`, { name: 'now', arguments: {} });
        nowOut.textContent = JSON.stringify(data, null, 2);
      } catch (err) { nowOut.textContent = String(err); }
    };

    document.getElementById('btnWeather').onclick = async () => {
      try {
        const city = document.getElementById('city').value || 'Tel Aviv';
        const data = await postJSON(`${BASE}/call`, { name: 'weather', arguments: { city } });
        weatherOut.textContent = JSON.stringify(data, null, 2);
      } catch (err) { weatherOut.textContent = String(err); }
    };

    document.getElementById('btnAsk').onclick = async () => {
      try {
        const prompt = document.getElementById('prompt').value.trim();
        const model = document.getElementById('model').value.trim();
        const args = model ? { prompt, model } : { prompt };
        const data = await postJSON(`${BASE}/call`, { name: 'ask_llm', arguments: args });
        askOut.textContent = JSON.stringify(data, null, 2);
      } catch (err) { askOut.textContent = String(err); }
    };
  </script>
</body>
</html>
```

### הפעלה
- ודא שהשרת רץ: `python -m server.app`
- פתח את הקובץ `web/index.html` בדפדפן (לדוגמה VSCode Live Server, או `python -m http.server` מתוך `web/`).
- לחץ על הכפתורים ובדוק את התגובות.

> אם אתה מקבל שגיאת CORS — ודא שהוספת `flask-cors` ו-`CORS(app)` כמו למעלה.

---

## 6) CLI אינטראקטיבי (Python)

**client/cli.py**
```python
import asyncio
import httpx
from typing import Any, Dict

BASE_URL = "http://127.0.0.1:5000"

async def call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE_URL}/call", json={"name": name, "arguments": arguments}, timeout=120)
        resp.raise_for_status()
        return resp.json()

async def main() -> None:
    print("MCP CLI — choose a tool:\n1) now\n2) weather\n3) ask_llm\n0) exit")
    while True:
        choice = input("Enter choice (0-3): ").strip()
        if choice == "0":
            print("Bye!")
            return
        elif choice == "1":
            data = await call_tool("now", {})
            print(data)
        elif choice == "2":
            city = input("City: ").strip() or "Tel Aviv"
            data = await call_tool("weather", {"city": city})
            print(data)
        elif choice == "3":
            prompt = input("Prompt: ").strip() or "Explain MCP in one sentence."
            model = input("Model (leave empty for default): ").strip()
            args = {"prompt": prompt}
            if model:
                args["model"] = model
            data = await call_tool("ask_llm", args)
            print(data)
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    asyncio.run(main())
```

### הרצה
```bash
# From project root, with server running
python -m client.cli
```

---

## 7) הרצה כוללת — צ׳ק-ליסט
1. הפעל Ollama (אם צריך: `ollama serve`) והתקן מודל (`ollama pull llama3.2:3b`).
2. הפעל venv והתקן תלויות (`pip install -r requirements.txt`).
3. הרץ את השרת: `python -m server.app`.
4. Frontend: פתח `web/index.html` בדפדפן (או הרץ `python -m http.server` בתיקיית `web`).
5. CLI: `python -m client.cli`.

---

## 8) Troubleshooting
- **`Unknown tool`** — ודא שהוספת את הכלי ל-`/tools` וגם לטיפול ב-`/call`.
- **`ModuleNotFoundError`** — הרץ כמודול: `python -m server.app`; ודא `__init__.py` קיים ב-`tools/`.
- **CORS errors** — ודא התקנה ושימוש ב-`flask-cors` ו-`CORS(app)`.
- **Ollama 400 / model null** — ודא שתמיד יש `model` (ברירת מחדל בקוד) וש-Ollama רץ.
- **Weather failures** — נדרש אינטרנט פתוח ל-Open-Meteo.

---

## 9) Optional: Tests (pytest)
הריץ שרת בחלון נפרד, ואז:
```bash
pytest -q
```
הוסף טסט שמוודא ש-`ask_llm` מחזיר טקסט שמכיל "Model Context Protocol" ולא מכיל "Microsoft Certified".

---

בהצלחה! אם תרצה, אכין גם Dockerfile ו-docker-compose להפעלה בלחיצה אחת, או אשדרג את ה-UI לעיצוב מודרני יותר (React/Tailwind).

