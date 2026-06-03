import httpx

from app.core.config import settings


class LLMCallerError(Exception):
    pass


def get_llm_api_key() -> str:
    api_key = settings.OPENROUTER_API_KEY

    if not api_key:
        raise LLMCallerError("OPENROUTER_API_KEY is missing in .env")

    return api_key


def get_llm_base_url() -> str:
    return settings.OPENROUTER_BASE_URL.rstrip("/")


def get_llm_model(model: str | None = None) -> str:
    return model or settings.OPENROUTER_MODEL


async def call_llm(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
    timeout_seconds: float = 120.0,
) -> str:
    api_key = get_llm_api_key()
    base_url = get_llm_base_url()
    selected_model = get_llm_model(model)

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Praxis Backend",
    }

    payload = {
        "model": selected_model,
        "messages": messages,
        "temperature": temperature,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise LLMCallerError(
            f"OpenRouter API error {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        raise LLMCallerError(
            f"Could not connect to OpenRouter API: {type(e).__name__}: {repr(e)}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallerError(
            f"Unexpected OpenRouter response shape: {e}. Response: {data}"
        )

    if not content:
        raise LLMCallerError("OpenRouter returned empty content")

    return content