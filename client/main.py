import asyncio
from typing import Any, Dict, List
import httpx

BASE_URL = "http://127.0.0.1:5000"

async def list_tools(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Call GET /tools and return the tools list."""
    resp = await client.get(f"{BASE_URL}/tools", timeout=10.0)
    resp.raise_for_status()
    data = resp.json()
    return data.get("tools", [])

async def call_tool(client: httpx.AsyncClient, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call POST /call with tool name + arguments."""
    payload = {"name": name, "arguments": arguments}
    resp = await client.post(f"{BASE_URL}/call", json=payload, timeout=20.0)
    resp.raise_for_status()
    return resp.json()

async def main() -> None:
    async with httpx.AsyncClient() as client:
        # 1) List tools
        tools = await list_tools(client)
        print("== Tools ==")
        for t in tools:
            print(f"- {t['name']}: {t.get('description','')}")
        print()

        # 2) Call 'now'
        print("== Call: now ==")
        now_res = await call_tool(client, "now", {})
        print(now_res)
        print()

        # 3) Call 'weather'
        print("== Call: weather (Tel Aviv) ==")
        w_res = await call_tool(client, "weather", {"city": "Tel Aviv"})
        print(w_res)

if __name__ == "__main__":
    asyncio.run(main())
