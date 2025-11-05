# tools/llm.py
import httpx
from typing import Dict, Any, Optional

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.2:3b"

# Strong, always-on system prompt to avoid Microsoft meaning
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

    model = model or DEFAULT_MODEL          # ensure non-empty model
    system = system or DEFAULT_SYSTEM       # ensure steering even if None

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
