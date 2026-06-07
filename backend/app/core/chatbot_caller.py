import httpx

from app.core.config import settings


class ChatbotCallerError(Exception):
    pass


async def call_chatbot(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.0,
    json_mode: bool = False,
    timeout_seconds: float = 120.0,
) -> str:
    """
    OpenAI-compatible call using CHATBOT_* env vars (Groq or any compatible provider).
    Used by chat, roadmap generation, and goal-related LLM calls.
    """
    api_key = settings.CHATBOT_API_KEY
    base_url = settings.CHATBOT_BASE_URL.rstrip("/")
    model = settings.CHATBOT_LLM_MODEL

    url = f"{base_url}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload: dict = {
        "model": model,
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
        status = e.response.status_code
        if status in (400, 401, 402, 404):
            print(f"\n[CHATBOT DIAGNOSTIC] API Error {status}:")
            print(f" -> Model : {model}")
            print(f" -> URL   : {base_url}")
            print(f" -> Check CHATBOT_API_KEY, CHATBOT_BASE_URL, CHATBOT_LLM_MODEL in .env\n")
        raise ChatbotCallerError(
            f"Chatbot API error {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        print(f"\n[CHATBOT DIAGNOSTIC] Connection Error — could not reach {base_url}\n")
        raise ChatbotCallerError(
            f"Could not connect to chatbot API: {type(e).__name__}: {repr(e)}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise ChatbotCallerError(
            f"Unexpected chatbot response shape: {e}. Response: {data}"
        )

    if not content:
        raise ChatbotCallerError("Chatbot returned empty content")

    return content
