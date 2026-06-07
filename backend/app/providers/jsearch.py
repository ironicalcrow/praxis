from typing import List
from datetime import datetime
import httpx

from app.core.config import settings
from .base import BaseJobScraper
from .schemas import RawScrapedJob


class JSearchScraper(BaseJobScraper):
    def __init__(self):
        super().__init__()
        keys_str = settings.JSEARCH_API_KEYS
        self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        self.current_key_index = 0

    @property
    def provider_name(self) -> str:
        return "jsearch"

    def _get_current_key(self) -> str:
        if not self.api_keys:
            raise ValueError("No JSearch API keys found in JSEARCH_API_KEYS environment variable.")
        return self.api_keys[self.current_key_index]

    def _rotate_key(self):
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"[JSearchProvider] API key exhausted. Rotating to key index: {self.current_key_index}")

    async def search_jobs(
        self,
        query: str,
        location: str = "",
        limit: int = 200,
    ) -> List[RawScrapedJob]:
        if not self.api_keys:
            print("[JSearchProvider] Missing JSEARCH_API_KEYS in environment.")
            return []

        # Avoid "query in location in location" when LLM already embedded location
        if location and location.lower() not in query.lower():
            full_query = f"{query} in {location}"
        else:
            full_query = query

        print(f"[JSearchProvider] full_query={full_query!r}")
        url = settings.JSEARCH_URL
        max_retries = len(self.api_keys)

        import time
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                key = self._get_current_key()
                headers = {
                    "X-RapidAPI-Key": key,
                    "X-RapidAPI-Host": settings.JSEARCH_API_HOST,
                }
                params = {
                    "query": full_query,
                    "num_pages": "20",
                }

                try:
                    start_t = time.time()
                    response = await client.get(url, headers=headers, params=params)
                    elapsed = time.time() - start_t
                    print(f"[JSearchProvider] Response in {elapsed:.2f}s for '{full_query}'")

                    if response.status_code in [429, 403]:
                        print(f"[JSearchProvider] Rate limit on key index {self.current_key_index} (HTTP {response.status_code})")
                        self._rotate_key()
                        continue

                    response.raise_for_status()
                    data = response.json()
                    items = data.get("data", [])
                    print(f"[JSearchProvider] Raw items returned: {len(items)} for '{full_query}'")

                    jobs = []
                    for item in items[:limit]:
                        job_id = item.get("job_id", "")
                        if not job_id:
                            continue
                        title = item.get("job_title", "Unknown Title")
                        company = item.get("employer_name", "Unknown Company")
                        job_url = item.get("job_apply_link") or item.get("job_google_link", "")
                        job_location = f"{item.get('job_city', '')}, {item.get('job_country', '')}".strip(", ")
                        description = item.get("job_description", "")

                        jobs.append(RawScrapedJob(
                            provider_id=self.provider_name,
                            job_id=job_id,
                            title=title,
                            company_name=company,
                            location=job_location,
                            url=job_url if job_url else "https://jsearch.p.rapidapi.com",
                            raw_text_content=description,
                            raw_json_data=item,
                            posted_at=datetime.utcnow(),
                        ))
                    return jobs

                except Exception as e:
                    print(f"[JSearchProvider] Error on attempt {attempt + 1}: {e}")
                    if attempt == max_retries - 1:
                        break
                    self._rotate_key()

        return []

    async def get_job_details(self, url: str) -> str:
        return "Full details already fetched from JSearch search endpoint."
