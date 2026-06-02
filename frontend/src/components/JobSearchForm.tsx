import { useState } from "react";
import type { JobSearchRequest } from "../types/jobs";

type JobSearchFormProps = {
  onSearch: (values: JobSearchRequest) => void;
  isLoading: boolean;
};

export default function JobSearchForm({
  onSearch,
  isLoading,
}: JobSearchFormProps) {
  const [query, setQuery] = useState("Machine Learning Internship");
  const [location, setLocation] = useState("Dhaka");
  const [numPages, setNumPages] = useState(1);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!query.trim()) {
      return;
    }

    onSearch({
      query,
      location,
      page: 1,
      num_pages: numPages,
    });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl"
    >
      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Job query
          </label>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. ML internship"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-blue-500"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Location
          </label>
          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="e.g. Dhaka"
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-blue-500"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Number of pages
          </label>
          <input
            type="number"
            min={1}
            max={5}
            value={numPages}
            onChange={(event) => setNumPages(Number(event.target.value))}
            className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition focus:border-blue-500"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="mt-5 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
      >
        {isLoading ? "Searching..." : "Find jobs"}
      </button>
    </form>
  );
}