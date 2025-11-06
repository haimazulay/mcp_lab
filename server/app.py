# app.py - FIXED VERSION
import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, request, jsonify
from flask_cors import CORS

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession


app = Flask(__name__)
CORS(app)  # Allow cross-origin requests


# ---- Server selection helpers ----
PREF_ORDER = ["mcp_server.py", "mcp_server_demo.py", "mcp_server_system.py"]

def _server_path_by_name(name: str) -> str:
    """Translate logical name to file name."""
    mapping = {
        "default": None,
        "demo": "mcp_server_demo.py",
        "system": "mcp_server_system.py",
        "lab": "mcp_server.py",
    }
    fname = mapping.get(name, None)
    if fname is None:
        return _default_server_path()
    p = Path(__file__).with_name(fname)
    return str(p)


def _default_server_path() -> str:
    """Pick first existing server file in preference order."""
    here = Path(__file__).parent
    for fname in PREF_ORDER:
        p = here / fname
        if p.exists():
            print(f"[DEBUG] Using default server: {fname}", file=sys.stderr)
            return str(p)
    return str(here / "mcp_server_demo.py")


# ---- Core MCP helpers ----
async def _with_session(server_path: str, coro):
    """Create a short-lived MCP stdio session."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-u", server_path],
        cwd=str(Path(server_path).parent),
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await coro(session)


def _serialize_tool_list(tools_result) -> Dict[str, Any]:
    """Flatten MCP ToolsResult to JSON."""
    tools = []
    for t in tools_result.tools:
        tools.append({
            "name": t.name,
            "description": getattr(t, "description", None),
            "inputSchema": getattr(t, "inputSchema", None),
        })
    return {"tools": tools}


def _serialize_tool_response(resp) -> Dict[str, Any]:
    """Flatten MCP ToolResponse to JSON - FIXED VERSION."""
    out: List[Dict[str, Any]] = []
    
    # Debug: print raw response
    print(f"[DEBUG] Raw response type: {type(resp)}", file=sys.stderr)
    print(f"[DEBUG] Raw response: {resp}", file=sys.stderr)
    
    # Extract content
    content = getattr(resp, "content", []) or []
    print(f"[DEBUG] Content items: {len(content)}", file=sys.stderr)
    
    for c in content:
        ctype = getattr(c, "type", None)
        print(f"[DEBUG] Content type: {ctype}", file=sys.stderr)
        
        if ctype == "text":
            text_val = getattr(c, "text", None)
            print(f"[DEBUG] Text value: {text_val}", file=sys.stderr)
            out.append({"type": "text", "text": text_val})
            
        elif ctype == "json":
            json_val = getattr(c, "json", None)
            print(f"[DEBUG] JSON value: {json_val}", file=sys.stderr)
            
            # Handle if json is a string that needs parsing
            if isinstance(json_val, str):
                try:
                    json_val = json.loads(json_val)
                except:
                    pass
            
            out.append({"type": "json", "json": json_val})
        else:
            # Other types
            item = {"type": ctype}
            for k in ("mimeType", "data", "annotations"):
                if hasattr(c, k):
                    item[k] = getattr(c, k)
            out.append(item)

    result = {
        "ok": True,
        "meta": getattr(resp, "meta", None),
        "content": out,
        "is_error": getattr(resp, "is_error", False),
    }
    
    print(f"[DEBUG] Final result: {result}", file=sys.stderr)
    return result


# ---- Routes ----
@app.get("/tools")
def http_tools():
    """GET /tools?server=demo|system|lab|default"""
    server_name = (request.args.get("server") or "default").strip().lower()
    server_path = _server_path_by_name(server_name)
    
    print(f"[DEBUG] Loading tools from: {server_path}", file=sys.stderr)

    def _coro(session: ClientSession):
        return session.list_tools()

    try:
        tools_result = asyncio.run(_with_session(server_path, _coro))
        payload = _serialize_tool_list(tools_result)
        payload["server"] = server_name
        payload["server_path"] = server_path
        payload["ok"] = True
        return jsonify(payload)
    except Exception as e:
        print(f"[ERROR] Failed to load tools: {e}", file=sys.stderr)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.post("/call")
def http_call():
    """POST /call - Body: {name, arguments, server?}"""
    data = request.get_json(force=True, silent=False) or {}
    name = data.get("name")
    args = data.get("arguments") or {}
    server_name = (data.get("server") or "default").strip().lower()

    if not name or not isinstance(args, dict):
        return jsonify({
            "ok": False,
            "error": "Invalid body. Expect {name: str, arguments: object}."
        }), 400

    server_path = _server_path_by_name(server_name)
    
    print(f"[DEBUG] Calling {name} on {server_path} with args: {args}", file=sys.stderr)

    def _coro(session: ClientSession):
        return session.call_tool(name, args)

    try:
        resp = asyncio.run(_with_session(server_path, _coro))
        payload = _serialize_tool_response(resp)
        payload["server"] = server_name
        payload["server_path"] = server_path
        payload["tool"] = name
        return jsonify(payload)
    except Exception as e:
        print(f"[ERROR] Tool call failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({
            "ok": False,
            "error": str(e),
            "server": server_name,
            "server_path": server_path
        }), 500


# ---- Health check ----
@app.get("/")
def health():
    return jsonify({"status": "running", "message": "MCP Flask Server"})


# ---- Entrypoint ----
if __name__ == "__main__":
    print("=" * 60)
    print("MCP Flask Server Starting...")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=True)