import type { JobCardType } from "../types/jobs";

type JobCardProps = {
  job: JobCardType;
};

function shortenText(text: string, maxLength: number) {
  if (text.length <= maxLength) {
    return text;
  }

  return text.slice(0, maxLength) + "...";
}

export default function JobCard({ job }: JobCardProps) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900 p-5 shadow-md transition hover:border-blue-500">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h3 className="text-xl font-bold text-white">{job.title}</h3>
          <p className="mt-1 text-slate-300">{job.company}</p>
          <p className="mt-1 text-sm text-slate-400">{job.location}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          {job.employment_type && (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              {job.employment_type}
            </span>
          )}

          {job.source && (
            <span className="rounded-full bg-blue-950 px-3 py-1 text-xs text-blue-300">
              {job.source}
            </span>
          )}
        </div>
      </div>

      {job.salary_range && (
        <p className="mt-4 text-sm font-medium text-emerald-400">
          Salary: {job.salary_range}
        </p>
      )}

      {job.posted_at && (
        <p className="mt-2 text-sm text-slate-400">Posted: {job.posted_at}</p>
      )}

      {job.description && (
        <p className="mt-4 text-sm leading-6 text-slate-300">
          {shortenText(job.description, 320)}
        </p>
      )}

      {job.job_url && (
        <a
          href={job.job_url}
          target="_blank"
          rel="noreferrer"
          className="mt-5 inline-flex rounded-xl border border-blue-500 px-4 py-2 text-sm font-semibold text-blue-300 transition hover:bg-blue-500 hover:text-white"
        >
          View job
        </a>
      )}
    </article>
  );
}