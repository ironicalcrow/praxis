import re
from typing import List
from app.providers.schemas import RawScrapedJob

def normalize_string(s: str) -> str:
    """Lowercases, removes punctuation, and normalizes spacing for comparison."""
    if not s:
        return ""
    # Lowercase
    s = s.lower()
    # Remove common company suffixes
    s = re.sub(r'\b(ltd|inc|llc|corp|corporation|limited|company|co|group)\b\.?', '', s)
    # Remove all non-alphanumeric characters
    s = re.sub(r'[^a-z0-9]', '', s)
    return s.strip()

def deduplicate_raw_jobs(jobs: List[RawScrapedJob]) -> List[RawScrapedJob]:
    """
    Filters out cross-provider duplicates by normalizing company and title.
    Keeps the first occurrence (we prioritize the provider order passed in).
    """
    seen_signatures = set()
    unique_jobs = []
    duplicates_removed = 0
    
    for job in jobs:
        comp = normalize_string(job.company_name)
        title = normalize_string(job.title)
        
        # Fallback if normalization strips everything
        if not comp:
            comp = job.company_name.lower().replace(" ", "") if job.company_name else "unknown"
        if not title:
            title = job.title.lower().replace(" ", "") if job.title else "unknown"
            
        signature = f"{comp}::{title}"
        
        if signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_jobs.append(job)
        else:
            duplicates_removed += 1
            print(f"[Deduplicator] Removed duplicate: {job.title} at {job.company_name} (Provider: {job.provider_id})")
            
    print(f"[Deduplicator] Finished. Kept {len(unique_jobs)} unique jobs. Removed {duplicates_removed} duplicates.")
    return unique_jobs
