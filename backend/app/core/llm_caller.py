import httpx

from app.core.config import settings


class LLMCallerError(Exception):
    pass


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
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        headers["HTTP-Referer"] = "http://localhost:8000"
        headers["X-Title"] = "Praxis Backend"

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
        status = e.response.status_code
        if status in (404, 402, 401, 400):
            print(f"\n[LLM DIAGNOSTIC] API Error {status}:")
            print(f" -> Check your .env file!")
            print(f" -> Current Model: {selected_model}")
            print(f" -> Base URL: {base_url}")
            print(f" -> If you see 'model not found' (404), ensure the model name is correct (e.g., 'deepseek/deepseek-chat' for OpenRouter, or 'llama3.1' for local Ollama).")
            print(f" -> If you see 'insufficient credits' (402), change your LLM_MODEL and LLM_BASE_URL to point to a free local endpoint like Ollama.\n")
            
        raise LLMCallerError(
            f"LLM API error {e.response.status_code}: {e.response.text}"
        )

    except httpx.RequestError as e:
        print(f"\n[LLM DIAGNOSTIC] Connection Error:")
        print(f" -> Could not reach the LLM provider at {base_url}.")
        print(f" -> If using local Ollama, make sure the Ollama app is actually running!\n")
        raise LLMCallerError(
            f"Could not connect to LLM API: {type(e).__name__}: {repr(e)}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallerError(
            f"Unexpected LLM response shape: {e}. Response: {data}"
        )

    if not content:
        raise LLMCallerError("LLM returned empty content")

    return content


async def embed_text(text: str, model: str | None = None) -> list[float]:
    """
    Generates a dense vector embedding using the configured embedding endpoint.
    Defaults to the local Ollama model (e.g. nomic-embed-text).
    """
    api_key = get_embedding_api_key()
    base_url = get_embedding_base_url()
    selected_model = model or get_embedding_model()

    url = f"{base_url}/embeddings"

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": selected_model,
        "input": text
    }

    timeout = httpx.Timeout(60.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
    except httpx.HTTPStatusError as e:
        raise LLMCallerError(f"Embeddings API error {e.response.status_code}: {e.response.text}")
        
    except httpx.RequestError as e:
        raise LLMCallerError(f"Could not connect to Embeddings API: {type(e).__name__}: {repr(e)}")

    data = response.json()

    try:
        embedding = data["data"][0]["embedding"]
        return embedding
    except (KeyError, IndexError, TypeError) as e:
        raise LLMCallerError(f"Unexpected Embeddings response shape: {e}. Response: {data}")
