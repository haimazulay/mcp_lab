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