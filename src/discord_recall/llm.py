"""OpenRouter LLM client."""

import httpx
from loguru import logger

from discord_recall.config import get_settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def complete(system: str, user_prompt: str) -> str:
    """Call OpenRouter chat completions API."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise SystemExit("OPENROUTER_API_KEY is not set in .env")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openrouter_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 4096,
            },
        )
        response.raise_for_status()
        data = response.json()

    choice = data["choices"][0]
    text = choice["message"]["content"]
    usage = data.get("usage", {})
    logger.debug(
        f"LLM: {usage.get('prompt_tokens', '?')} in / "
        f"{usage.get('completion_tokens', '?')} out "
        f"({settings.openrouter_model})"
    )
    return text
