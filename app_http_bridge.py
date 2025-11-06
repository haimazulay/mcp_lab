#!/usr/bin/env python3
# app_http_bridge.py
import os, sys, asyncio
from pathlib import Path
from typing import Dict, Any, Callable

from flask import Flask, request, jsonify
from flask_cors import CORS

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

app = Flask(__name__)
CORS(app)

def log(msg: str) -> None:
    print(f"[bridge] {msg}", file=sys.stderr, flush=True)

BASE_DIR = Path(__file__).resolve().parent

def server_path(which: str) -> Path:
    fname = "mcp_server_demo.py" if which == "demo" else "mcp_server_system.py"
    return BASE_DIR / fname

from typing import Awaitable

async def run_with_session(which: str, runner: Callable[[ClientSession], Awaitable[Any]]):
    srv = server_path(which)
    if not srv.exists():
        raise FileNotFoundError(f"Server file not found: {srv}")

    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", str(srv)],
        cwd=str(BASE_DIR),
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )

    log(f"launch: {params.command} {' '.join(params.args)} (cwd={params.cwd})")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            log("initialize…")
            await asyncio.wait_for(session.initialize(), timeout=10)
            log("initialized.")
            res = await asyncio.wait_for(runner(session), timeout=20)
            log("runner done.")
            return res

@app.get("/")
def health():
    return jsonify({"ok": True, "service": "mcp-http-bridge", "cwd": str(BASE_DIR)})

@app.get("/tools")
def tools():
    which = request.args.get("server", "demo")
    try:
        async def job(session: ClientSession):
            return await session.list_tools()
        resp = asyncio.run(run_with_session(which, job))
        out = [{"name": t.name, "description": t.description} for t in resp.tools]
        return jsonify({"server": which, "tools": out})
    except asyncio.TimeoutError:
        log("timeout in /tools")
        return jsonify({"ok": False, "error": "timeout"}), 504
    except FileNotFoundError as e:
        log(str(e))
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        log(f"/tools error: {e!r}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/call")
def call():
    data: Dict[str, Any] = request.get_json(force=True) or {}
    name = data.get("name")
    args = data.get("arguments") or {}
    which = data.get("server", "demo")

    if not name:
        return jsonify({"ok": False, "error": "missing 'name'"}), 400
    if not isinstance(args, dict):
        return jsonify({"ok": False, "error": "arguments must be an object"}), 400

    try:
        def job(session: ClientSession):
            return session.call_tool(name, arguments=args)
        resp = asyncio.run(run_with_session(which, job))
        blocks = []
        for c in getattr(resp, "content", []) or []:
            t = getattr(c, "type", None)
            if t == "json":
                blocks.append({"type": "json", "json": getattr(c, "json", None)})
            elif t == "text":
                blocks.append({"type": "text", "text": getattr(c, "text", None)})
        return jsonify({"ok": True, "server": which, "tool": name, "content": blocks})
    except asyncio.TimeoutError:
        log("timeout in /call")
        return jsonify({"ok": False, "error": "timeout"}), 504
    except FileNotFoundError as e:
        log(str(e))
        return jsonify({"ok": False, "error": str(e)}), 500
    except Exception as e:
        log(f"/call error: {e!r}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    # threaded=True עוזר בסביבות Windows מסוימות
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
