import httpx

from app.core.config import settings

_FALLBACK_CODES = {429, 402, 503}


class LLMCallerError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def get_llm_api_key() -> str | None:
    return settings.LLM_API_KEY

def get_llm_base_url() -> str:
    return settings.LLM_BASE_URL.rstrip("/")

def get_llm_model(model: str | None = None) -> str:
    return model or settings.LLM_MODEL

def get_embedding_api_key() -> str | None:
    if settings.EMBEDDING_API_KEY:
        return settings.EMBEDDING_API_KEY
    if get_embedding_base_url() == get_llm_base_url():
        return settings.LLM_API_KEY
    return None

def get_embedding_base_url() -> str:
    url = settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL
    return url.rstrip("/")

def get_embedding_model() -> str:
    return settings.EMBEDDING_MODEL


async def _call_provider(
    api_key: str | None,
    base_url: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    json_mode: bool,
    timeout_seconds: float,
) -> str:
    url = f"{base_url.rstrip('/')}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "Praxis Backend"

    payload: dict = {"model": model, "messages": messages, "temperature": temperature}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    timeout = httpx.Timeout(timeout_seconds, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (404, 402, 401, 400):
            print(f"\n[LLM DIAGNOSTIC] API Error {status}:")
            print(f" -> Model: {model} | URL: {base_url}")
            print(f" -> Check LLM_API_KEY / LLM_BASE_URL / LLM_MODEL in .env\n")
        raise LLMCallerError(
            f"LLM API error {status}: {e.response.text}",
            status_code=status,
        )

    except httpx.RequestError as e:
        print(f"\n[LLM DIAGNOSTIC] Connection Error — could not reach {base_url}\n")
        raise LLMCallerError(f"Could not connect to LLM API: {type(e).__name__}: {repr(e)}")

    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallerError(f"Unexpected LLM response shape: {e}. Response: {data}")

    if not content:
        raise LLMCallerError("LLM returned empty content")

    return content


async def call_llm(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
    timeout_seconds: float = 120.0,
) -> str:
    try:
        return await _call_provider(
            api_key=get_llm_api_key(),
            base_url=get_llm_base_url(),
            model=get_llm_model(model),
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds,
        )
    except LLMCallerError as primary_err:
        if primary_err.status_code not in _FALLBACK_CODES or not settings.LLM_FALLBACK_API_KEY:
            raise
        print(f"[LLM] Primary provider returned {primary_err.status_code} — trying fallback provider...")
        return await _call_provider(
            api_key=settings.LLM_FALLBACK_API_KEY,
            base_url=(settings.LLM_FALLBACK_BASE_URL or settings.LLM_BASE_URL).rstrip("/"),
            model=settings.LLM_FALLBACK_MODEL or get_llm_model(model),
            messages=messages,
            temperature=temperature,
            json_mode=json_mode,
            timeout_seconds=timeout_seconds,
        )


async def _embed_provider(
    api_key: str | None,
    base_url: str,
    model: str,
    text: str,
    timeout: httpx.Timeout,
) -> list[float]:
    url = f"{base_url.rstrip('/')}/embeddings"

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json={"model": model, "input": text})
            response.raise_for_status()

    except httpx.HTTPStatusError as e:
        raise LLMCallerError(
            f"Embeddings API error {e.response.status_code}: {e.response.text}",
            status_code=e.response.status_code,
        )

    except httpx.RequestError as e:
        raise LLMCallerError(f"Could not connect to Embeddings API: {type(e).__name__}: {repr(e)}")

    data = response.json()
    try:
        return data["data"][0]["embedding"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallerError(f"Unexpected Embeddings response shape: {e}. Response: {data}")


async def embed_text(text: str, model: str | None = None) -> list[float]:
    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        return await _embed_provider(
            api_key=get_embedding_api_key(),
            base_url=get_embedding_base_url(),
            model=model or get_embedding_model(),
            text=text,
            timeout=timeout,
        )
    except LLMCallerError as primary_err:
        if primary_err.status_code not in _FALLBACK_CODES or not settings.EMBEDDING_FALLBACK_API_KEY:
            raise
        print(f"[Embeddings] Primary provider returned {primary_err.status_code} — trying fallback provider...")
        return await _embed_provider(
            api_key=settings.EMBEDDING_FALLBACK_API_KEY,
            base_url=(settings.EMBEDDING_FALLBACK_BASE_URL or settings.EMBEDDING_BASE_URL).rstrip("/"),
            model=settings.EMBEDDING_FALLBACK_MODEL or model or get_embedding_model(),
            text=text,
            timeout=timeout,
        )
