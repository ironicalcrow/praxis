import httpx

from app.core.config import settings

_FALLBACK_CODES = {429, 402, 503}


class ChatbotCallerError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


async def _call_chatbot_provider(
    api_key: str,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool,
    timeout_seconds: float,
    tools: list[dict] | None = None,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
        payload["parallel_tool_calls"] = False

    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (400, 401, 402, 404):
            print(f"\n[CHATBOT DIAGNOSTIC] API Error {status}:")
            print(f" -> Model: {model} | URL: {base_url}")
            print(f" -> Check CHATBOT_API_KEY / CHATBOT_BASE_URL / CHATBOT_LLM_MODEL in .env\n")
        raise ChatbotCallerError(
            f"Chatbot API error {status}: {e.response.text}",
            status_code=status,
        )

    except httpx.RequestError as e:
        print(f"\n[CHATBOT DIAGNOSTIC] Connection Error — could not reach {base_url}\n")
        raise ChatbotCallerError(f"Could not connect to chatbot API: {type(e).__name__}: {repr(e)}")

    data = response.json()
    try:
        message = data["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as e:
        raise ChatbotCallerError(f"Unexpected chatbot response shape: {e}. Response: {data}")

    # Tool call response — return structured dict for the agentic loop
    if message.get("tool_calls"):
        return {"tool_calls": message["tool_calls"]}

    content = message.get("content")
    if not content:
        raise ChatbotCallerError("Chatbot returned empty content")

    return content


async def call_chatbot(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    json_mode: bool = False,
    timeout_seconds: float = 120.0,
    tools: list[dict] | None = None,
) -> str:
    """
    OpenAI-compatible call using CHATBOT_* env vars (Groq or any compatible provider).
    Automatically falls back to CHATBOT_FALLBACK_* on 429 / 402 / 503.
    Used by chat, roadmap generation, and goal-related LLM calls.
    """
    try:
        return await _call_chatbot_provider(
            api_key=settings.CHATBOT_API_KEY,
            base_url=settings.CHATBOT_BASE_URL,
            model=settings.CHATBOT_LLM_MODEL,
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds,
            tools=tools,
        )
    except ChatbotCallerError as primary_err:
        if primary_err.status_code not in _FALLBACK_CODES or not settings.CHATBOT_FALLBACK_API_KEY:
            raise
        print(f"[Chatbot] Primary provider returned {primary_err.status_code} — trying fallback provider...")
        return await _call_chatbot_provider(
            api_key=settings.CHATBOT_FALLBACK_API_KEY,
            base_url=(settings.CHATBOT_FALLBACK_BASE_URL or settings.CHATBOT_BASE_URL).rstrip("/"),
            model=settings.CHATBOT_FALLBACK_MODEL or settings.CHATBOT_LLM_MODEL,
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds,
            tools=tools,
        )
