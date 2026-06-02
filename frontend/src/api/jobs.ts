import type { JobCardType, JobSearchRequest } from "../types/jobs";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function searchLiveJobs(
  payload: JobSearchRequest
): Promise<JobCardType[]> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/live-search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to search jobs");
  }

  const data = await response.json();

  /**
   * This handles different possible backend shapes:
   * 1. [...]
   * 2. { jobs: [...] }
   * 3. { data: [...] }
   */
  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.jobs)) {
    return data.jobs;
  }

  if (Array.isArray(data.data)) {
    return data.data;
  }

  return [];
}