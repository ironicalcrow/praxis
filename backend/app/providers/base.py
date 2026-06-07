from abc import ABC, abstractmethod
from typing import List, AsyncGenerator
from app.providers.schemas import RawScrapedJob

class BaseJobScraper(ABC):
    """
    Abstract base class for all job board scrapers.
    Forces a consistent and robust interface for any new job board we integrate.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier for the job board (e.g., 'linkedin')."""
        pass

    @abstractmethod
    async def search_jobs(self, query: str, location: str = "", limit: int = 20) -> List[RawScrapedJob]:
        """
        Searches for jobs matching the query and returns basic details.
        Some providers might not include full descriptions in search results.
        """
        pass

    @abstractmethod
    async def get_job_details(self, url: str) -> str:
        """
        Fetches the full HTML or text description of a specific job posting.
        Returns the raw HTML/text string.
        """
        pass
        
    async def scrape_pipeline(self, query: str, location: str = "", limit: int = 20) -> AsyncGenerator[RawScrapedJob, None]:
        """
        A default pipeline that searches jobs and then fetches full details for each.
        Yields them one by one as they are fully scraped, which is useful for background streaming.
        """
        jobs = await self.search_jobs(query, location, limit)
        for job in jobs:
            # If the search endpoint didn't provide the full description, fetch it now
            if not job.raw_html_content and not job.raw_text_content:
                try:
                    content = await self.get_job_details(str(job.url))
                    job.raw_html_content = content
                except Exception as e:
                    # Log the error, but continue the pipeline so one failure doesn't break the batch
                    print(f"Error fetching details for {job.url}: {e}")
            yield job
