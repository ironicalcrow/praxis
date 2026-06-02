import { useState } from "react";
import { searchLiveJobs } from "../api/jobs";
import JobCard from "../components/JobCard";
import JobSearchForm from "../components/JobSearchForm";
import type { JobCardType, JobSearchRequest } from "../types/jobs";

export default function JobSearchPage() {
  const [jobs, setJobs] = useState<JobCardType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSearch(values: JobSearchRequest) {
    try {
      setIsLoading(true);
      setErrorMessage("");

      const results = await searchLiveJobs(values);
      setJobs(results);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Something went wrong";

      setErrorMessage(message);
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-6xl">
        <section className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-400">
            CareerPilot
          </p>

          <h1 className="mt-2 text-4xl font-bold">Job Hunter Agent</h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Search live jobs through the FastAPI backend and display normalized
            job cards from JSearch.
          </p>
        </section>

        <JobSearchForm onSearch={handleSearch} isLoading={isLoading} />

        {errorMessage && (
          <div className="mt-6 rounded-xl border border-red-800 bg-red-950 p-4 text-red-200">
            <p className="font-semibold">Something went wrong</p>
            <p className="mt-1 text-sm">{errorMessage}</p>
          </div>
        )}

        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-2xl font-bold">Results</h2>

            <p className="text-sm text-slate-400">
              {jobs.length} job{jobs.length === 1 ? "" : "s"} found
            </p>
          </div>

          {isLoading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-300">
              Searching live job sources...
            </div>
          )}

          {!isLoading && jobs.length === 0 && !errorMessage && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-300">
              No jobs yet. Search to see results.
            </div>
          )}

          <div className="grid gap-5 md:grid-cols-2">
            {jobs.map((job, index) => (
              <JobCard key={`${job.title}-${job.company}-${index}`} job={job} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}