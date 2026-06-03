import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    JSEARCH_API_KEY:str=os.getenv("JSEARCH_API_KEY")
    JSEARCH_API_HOST:str=os.getenv("JSEARCH_API_HOST")
    jsearch_URL:str=os.getenv("jsearch_URL")
    jsearch_detail_URL:str=os.getenv("jsearch_detail_URL")

    ENABLE_JOB_PROFILE_EXTRACTOR: bool = (
    os.getenv("ENABLE_JOB_PROFILE_EXTRACTOR", "false").lower() == "true"
    )

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "none").lower()

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL")
    OLLAMA_JOB_PROFILE_MODEL: str = os.getenv(
        "OLLAMA_JOB_PROFILE_MODEL",
    )

settings=Settings()