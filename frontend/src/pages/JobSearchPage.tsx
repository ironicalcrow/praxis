import { useState } from "react";
import { searchLiveJobs } from "../api/jobs";
import type { JobCardType, JobSearchRequest } from "../types/jobs";

export default function JobSearchPage() {
  const [query, setQuery] = useState("Machine Learning Internship");
  const [location, setLocation] = useState("Dhaka");
  const [jobs, setJobs] = useState<JobCardType[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const payload: JobSearchRequest = {
      query,
      location,
      page: 1,
      num_pages: 1,
    };

    try {
      setIsLoading(true);
      setErrorMessage("");

      const results = await searchLiveJobs(payload);
      setJobs(results);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong");
      setJobs([]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl p-6 lg:p-10">
      <section className="mb-8">
        <p className="text-sm font-bold uppercase tracking-wide text-indigo-600">
          CareerPilot
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">Job Hunter</h1>
        <p className="mt-3 max-w-2xl text-slate-500">
          Search live jobs and view normalized cards from your FastAPI backend.
        </p>
      </section>

      <form
        onSubmit={handleSearch}
        className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div className="grid gap-4 md:grid-cols-[1.4fr_1fr_auto]">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 outline-none focus:border-indigo-300 focus:bg-white"
            placeholder="Machine Learning Internship"
          />

          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-5 py-4 outline-none focus:border-indigo-300 focus:bg-white"
            placeholder="Dhaka"
          />

          <button
            type="submit"
            disabled={isLoading}
            className="rounded-2xl bg-indigo-600 px-8 py-4 font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:bg-slate-300"
          >
            {isLoading ? "Searching..." : "Hunt"}
          </button>
        </div>
      </form>

      {errorMessage && (
        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      <section className="mt-8">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-2xl font-bold">Results</h2>
          <p className="text-sm font-medium text-slate-500">{jobs.length} jobs found</p>
        </div>

        <div className="grid gap-5 xl:grid-cols-2">
          {jobs.map((job, index) => (
            <JobResultCard key={`${job.title}-${job.company}-${index}`} job={job} />
          ))}
        </div>

        {!isLoading && jobs.length === 0 && !errorMessage && (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
            No jobs yet. Search to see live results.
          </div>
        )}
      </section>
    </div>
  );
}

function JobResultCard({ job }: { job: JobCardType }) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-indigo-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold leading-snug">{job.title}</h3>
          <p className="mt-1 text-slate-500">{job.company}</p>
          <p className="mt-2 text-sm text-slate-500">{job.location}</p>
        </div>

        <span className="rounded-2xl bg-amber-50 px-3 py-2 text-sm font-bold text-amber-600">
          84% fit
        </span>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {job.employment_type && (
          <span className="rounded-xl bg-slate-100 px-3 py-1 text-sm font-medium text-slate-700">
            {job.employment_type}
          </span>
        )}

        {job.source && (
          <span className="rounded-xl bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-600">
            {job.source}
          </span>
        )}
      </div>

      {job.description && (
        <p className="mt-5 line-clamp-4 text-sm leading-6 text-slate-500">
          {job.description.slice(0, 350)}...
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        {job.job_url && (
          <a
            href={job.job_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-semibold text-white hover:bg-indigo-500"
          >
            Apply ↗
          </a>
        )}

        <button className="rounded-2xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-200">
          Save
        </button>

        <button className="rounded-2xl px-5 py-3 text-sm font-semibold text-slate-500 hover:bg-slate-100">
          Draft cover letter
        </button>
      </div>
    </article>
  );
}