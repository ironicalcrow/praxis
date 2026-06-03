const statCards = [
  {
    label: "Applications",
    value: "12",
    note: "+3 this week",
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
];

const recentApplications = [
  {
    role: "Machine Learning Intern",
    company: "Pathao",
    status: "Applied",
    fit: "92%",
    deadline: "Jun 18, 2026",
  },
  {
    role: "AI Engineer",
    company: "Brain Station 23",
    status: "Interviewing",
    fit: "84%",
    deadline: "Jun 30, 2026",
  },
  {
    role: "Full-Stack Engineer",
    company: "ShopUp",
    status: "Saved",
    fit: "76%",
    deadline: "Jul 5, 2026",
  },
];

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

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-7xl p-6 lg:p-10">
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

      <section className="mt-10 grid gap-7 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold tracking-tight">
                Recent Applications
              </h2>
              <p className="mt-1 text-slate-500">
                A quick overview of your current application pipeline.
              </p>
            </div>

            <span className="rounded-2xl bg-indigo-50 px-4 py-2 text-sm font-bold text-indigo-600">
              Demo data
            </span>
          </div>

          <div className="space-y-4">
            {recentApplications.map((application) => (
              <div
                key={`${application.role}-${application.company}`}
                className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
              >
                <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <h3 className="text-lg font-bold">{application.role}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {application.company}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-xl bg-white px-3 py-1 text-sm font-semibold text-slate-600">
                      {application.status}
                    </span>

                    <span className="rounded-xl bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-600">
                      {application.fit} fit
                    </span>

                    <span className="rounded-xl bg-amber-50 px-3 py-1 text-sm font-semibold text-amber-600">
                      Due {application.deadline}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
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