#!/usr/bin/env python3
# mcp_server_system.py
import sys
import platform
import getpass
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

# ---------- safe stderr logging ----------
def log(msg: str) -> None:
    """Log to stderr only; stdout is reserved for MCP protocol."""
    print(f"[server] {msg}", file=sys.stderr, flush=True)

# ---------- init ----------
mcp = FastMCP("mcp-system")
log("server boot")

# ---------- tool: system_info ----------
@mcp.tool()
def system_info() -> Dict[str, Any]:
    """Return basic local user/system info as structured JSON."""
    log("system_info() called")
    return {
        "username": getpass.getuser(),
        "os": platform.system() or "Unknown OS",
        "version": platform.version(),
    }

if __name__ == "__main__":
    # Run MCP over stdio
    mcp.run()
