import { useEffect, useMemo, useState } from "react";
import {
  fetchKanbanApplications,
  updateApplicationStatus,
  type KanbanApplications,
} from "../api/applications";
import type { Application, ApplicationStatus } from "../types/applications";

const DEMO_USER_ID = import.meta.env.VITE_DEMO_USER_ID;

const columns: {
  key: ApplicationStatus;
  title: string;
  description: string;
}[] = [
  {
    key: "saved",
    title: "Saved",
    description: "Jobs you saved for later.",
  },
  {
    key: "applied",
    title: "Applied",
    description: "Applications already submitted.",
  },
  {
    key: "interviewing",
    title: "Interviewing",
    description: "Companies you are talking to.",
  },
  {
    key: "offer",
    title: "Offer",
    description: "Offers or final-stage wins.",
  },
  {
    key: "rejected",
    title: "Rejected",
    description: "Closed or rejected applications.",
  },
];

const emptyKanban: KanbanApplications = {
  saved: [],
  applied: [],
  interviewing: [],
  offer: [],
  rejected: [],
};

const upcomingTasks = [
  {
    title: "Apply to 3 AI internships",
    due: "Today",
  },
  {
    title: "Review CV extraction results",
    due: "Tomorrow",
  },
  {
    title: "Practice SQL interview questions",
    due: "Friday",
  },
];

function formatDate(date?: string | null) {
  if (!date) {
    return "No date";
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(date));
}

function getColumnAccent(status: ApplicationStatus) {
  if (status === "saved") {
    return "bg-slate-100 text-slate-600";
  }

  if (status === "applied") {
    return "bg-indigo-50 text-indigo-600";
  }

  if (status === "interviewing") {
    return "bg-blue-50 text-blue-600";
  }

  if (status === "offer") {
    return "bg-emerald-50 text-emerald-600";
  }

  return "bg-red-50 text-red-600";
}

export default function DashboardPage() {
  const [kanban, setKanban] = useState<KanbanApplications>(emptyKanban);
  const [isLoadingApplications, setIsLoadingApplications] = useState(false);
  const [applicationsError, setApplicationsError] = useState("");
  const [updatingApplicationId, setUpdatingApplicationId] = useState("");

  async function loadKanbanApplications() {
    if (!DEMO_USER_ID) {
      setApplicationsError(
        "Missing VITE_DEMO_USER_ID in frontend/.env. Ask backend team for a test user UUID."
      );
      return;
    }

    try {
      setIsLoadingApplications(true);
      setApplicationsError("");

      const data = await fetchKanbanApplications(DEMO_USER_ID);

      setKanban({
        saved: data.saved ?? [],
        applied: data.applied ?? [],
        interviewing: data.interviewing ?? [],
        offer: data.offer ?? [],
        rejected: data.rejected ?? [],
      });
    } catch (error) {
      setApplicationsError(
        error instanceof Error
          ? error.message
          : "Failed to load Kanban applications"
      );
    } finally {
      setIsLoadingApplications(false);
    }
  }

  useEffect(() => {
    let cancelled = false;

    (async () => {
      if (!DEMO_USER_ID) {
        if (!cancelled) {
          setApplicationsError(
            "Missing VITE_DEMO_USER_ID in frontend/.env. Ask backend team for a test user UUID."
          );
        }
        return;
      }

      try {
        setIsLoadingApplications(true);
        setApplicationsError("");

        const data = await fetchKanbanApplications(DEMO_USER_ID);

        if (cancelled) return;

        setKanban({
          saved: data.saved ?? [],
          applied: data.applied ?? [],
          interviewing: data.interviewing ?? [],
          offer: data.offer ?? [],
          rejected: data.rejected ?? [],
        });
      } catch (error) {
        if (!cancelled) {
          setApplicationsError(
            error instanceof Error
              ? error.message
              : "Failed to load Kanban applications"
          );
        }
      } finally {
        if (!cancelled) setIsLoadingApplications(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const allApplications = useMemo(
    () => Object.values(kanban).flat(),
    [kanban]
  );

  const statCards = useMemo(
    () => [
      {
        label: "Applications",
        value: String(allApplications.length),
        note:
          allApplications.length === 1
            ? "1 tracked application"
            : `${allApplications.length} tracked applications`,
        icon: "▣",
        tone: "bg-indigo-50 text-indigo-600",
      },
      {
        label: "Active Goals",
        value: "4",
        note: "2 due soon",
        icon: "◎",
        tone: "bg-amber-50 text-amber-500",
      },
      {
        label: "Roadmap",
        value: "62%",
        note: "+8% this week",
        icon: "□",
        tone: "bg-emerald-50 text-emerald-600",
      },
      {
        label: "Streak",
        value: "9 days",
        note: "Keep going",
        icon: "♨",
        tone: "bg-orange-50 text-orange-500",
      },
    ],
    [allApplications.length]
  );

  async function handleStatusChange(
    application: Application,
    nextStatus: ApplicationStatus
  ) {
    if (application.status === nextStatus) {
      return;
    }

    try {
      setUpdatingApplicationId(application.id);

      await updateApplicationStatus({
        applicationId: application.id,
        userId: DEMO_USER_ID,
        status: nextStatus,
        reason: `Moved from ${application.status} to ${nextStatus} from dashboard Kanban board`,
      });

      await loadKanbanApplications();
    } catch (error) {
      setApplicationsError(
        error instanceof Error
          ? error.message
          : "Failed to update application status"
      );
    } finally {
      setUpdatingApplicationId("");
    }
  }

  return (
    <div className="mx-auto max-w-[1500px] p-6 lg:p-10">
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/70"
          >
            <div className="flex items-start justify-between">
              <p className="text-sm font-bold uppercase tracking-wide text-slate-500">
                {card.label}
              </p>

              <div
                className={`flex h-12 w-12 items-center justify-center rounded-2xl ${card.tone}`}
              >
                {card.icon}
              </div>
            </div>

            <h2 className="mt-3 text-4xl font-bold tracking-tight">
              {card.value}
            </h2>

            <p className="mt-2 text-sm font-medium text-emerald-600">
              {card.note}
            </p>
          </div>
        ))}
      </section>

      <section className="mt-10 grid gap-7 xl:grid-cols-[1.4fr_0.6fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">
                Application Board
              </h2>
              <p className="mt-1 text-slate-500">
                Track your applications by status.
              </p>
            </div>

            <span className="rounded-2xl bg-indigo-50 px-4 py-2 text-sm font-bold text-indigo-600">
              Kanban
            </span>
          </div>

          {isLoadingApplications && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 text-slate-500">
              Loading application board...
            </div>
          )}

          {applicationsError && !isLoadingApplications && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
              {applicationsError}
            </div>
          )}

          {!isLoadingApplications && !applicationsError && (
            <div className="overflow-x-auto pb-2">
              <div className="grid min-w-[1050px] grid-cols-5 gap-4">
                {columns.map((column) => (
                  <KanbanColumn
                    key={column.key}
                    column={column}
                    applications={kanban[column.key]}
                    updatingApplicationId={updatingApplicationId}
                    onStatusChange={handleStatusChange}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="mb-6">
            <h2 className="text-2xl font-bold tracking-tight">
              Today&apos;s Focus
            </h2>
            <p className="mt-1 text-slate-500">
              A simple task list for the day.
            </p>
          </div>

          <div className="space-y-4">
            {upcomingTasks.map((task) => (
              <div
                key={task.title}
                className="flex items-start gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4"
              >
                <div className="mt-1 h-3 w-3 rounded-full bg-indigo-600" />

                <div>
                  <h3 className="font-bold">{task.title}</h3>
                  <p className="mt-1 text-sm text-slate-500">{task.due}</p>
                </div>
              </div>
            ))}
          </div>
        </aside>
      </section>

      <section className="mt-7 rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
        <div className="grid gap-6 md:grid-cols-3">
          <QuickAction
            title="Find live jobs"
            description="Go to Job Hunter to search real openings."
            href="/jobs"
          />

          <QuickAction
            title="Upload your CV"
            description="Go to My CV to parse your resume."
            href="/cv"
          />

          <QuickAction
            title="Ask AI Assistant"
            description="Chat and get career guidance."
            href="/assistant"
          />
        </div>
      </section>
    </div>
  );
}

function KanbanColumn({
  column,
  applications,
  updatingApplicationId,
  onStatusChange,
}: {
  column: {
    key: ApplicationStatus;
    title: string;
    description: string;
  };
  applications: Application[];
  updatingApplicationId: string;
  onStatusChange: (
    application: Application,
    nextStatus: ApplicationStatus
  ) => void;
}) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
      <div className="mb-4">
        <div className="flex items-center justify-between gap-3">
          <h3 className="font-bold text-slate-950">{column.title}</h3>

          <span
            className={`rounded-full px-3 py-1 text-xs font-bold ${getColumnAccent(
              column.key
            )}`}
          >
            {applications.length}
          </span>
        </div>

        <p className="mt-1 text-xs leading-5 text-slate-500">
          {column.description}
        </p>
      </div>

      <div className="space-y-3">
        {applications.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-400">
            No applications
          </div>
        )}

        {applications.map((application) => (
          <KanbanCard
            key={application.id}
            application={application}
            updatingApplicationId={updatingApplicationId}
            onStatusChange={onStatusChange}
          />
        ))}
      </div>
    </div>
  );
}

function KanbanCard({
  application,
  updatingApplicationId,
  onStatusChange,
}: {
  application: Application;
  updatingApplicationId: string;
  onStatusChange: (
    application: Application,
    nextStatus: ApplicationStatus
  ) => void;
}) {
  const isUpdating = updatingApplicationId === application.id;

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-200 hover:shadow-md">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-bold leading-snug text-slate-950">
            {application.job_title}
          </h4>

          <p className="mt-1 text-sm text-slate-500">
            {application.company}
          </p>
        </div>
      </div>

      {application.location && (
        <p className="mt-3 text-xs font-medium text-slate-400">
          {application.location}
        </p>
      )}

      <div className="mt-3 flex flex-wrap gap-2">
        {application.salary && (
          <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-600">
            {application.salary}
          </span>
        )}

        {application.source && (
          <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-indigo-600">
            {application.source}
          </span>
        )}
      </div>

      <p className="mt-3 text-xs text-slate-400">
        Applied: {formatDate(application.applied_at)}
      </p>

      <select
        value={application.status}
        disabled={isUpdating}
        onChange={(event) =>
          onStatusChange(application, event.target.value as ApplicationStatus)
        }
        className="mt-4 w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700 outline-none transition focus:border-indigo-300 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {columns.map((column) => (
          <option key={column.key} value={column.key}>
            Move to {column.title}
          </option>
        ))}
      </select>

      {application.apply_url && (
        <a
          href={application.apply_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 block rounded-xl bg-indigo-600 px-3 py-2 text-center text-sm font-bold text-white transition hover:bg-indigo-500"
        >
          Open job ↗
        </a>
      )}
    </article>
  );
}

function QuickAction({
  title,
  description,
  href,
}: {
  title: string;
  description: string;
  href: string;
}) {
  return (
    <a
      href={href}
      className="rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:border-indigo-200 hover:bg-indigo-50"
    >
      <h3 className="text-lg font-bold">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
    </a>
  );
}