import { Link } from "react-router-dom";
import careerPilotLogo from "../assets/CareerPilot Logo.png";
import {
  ArrowRight,
  BriefcaseBusiness,
  FileText,
  Target,
  MessageSquare,
  BarChart3,
  Bell,
  CheckCircle2,
} from "lucide-react";

const features = [
  {
    title: "Job Hunter Agent",
    description:
      "Describe what you want. Your agent searches, ranks, and explains every fit with context from your CV.",
    icon: BriefcaseBusiness,
  },
  {
    title: "CV-Grounded RAG",
    description:
      "Upload once. Every agent can use your real experience, projects, skills, and education as context.",
    icon: FileText,
  },
  {
    title: "Skill Roadmap",
    description:
      "Pick a target role and get a focused roadmap based on the gap between your CV and the market.",
    icon: Target,
  },
  {
    title: "Interview Prep",
    description:
      "Practice questions tailored to your projects, target jobs, and current skill gaps.",
    icon: MessageSquare,
  },
  {
    title: "Progress Dashboard",
    description:
      "Track applications, roadmap progress, streaks, and goals from one clean dashboard.",
    icon: BarChart3,
  },
  {
    title: "Proactive Nudges",
    description:
      "Get reminders and next actions so your job hunt keeps moving instead of stalling.",
    icon: Bell,
  },
];

const steps = [
  {
    number: "01",
    title: "Drop your CV",
    description:
      "Upload your resume. CareerPilot extracts structured information and prepares it for every agent.",
  },
  {
    number: "02",
    title: "Pick a target",
    description:
      "Choose a role, location, or job query. Your agent starts searching with real context.",
  },
  {
    number: "03",
    title: "Let the agents work",
    description:
      "Search, rank, prep, roadmap, and nudge — you review the results and take action.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050719] text-white">
      <header className="sticky top-0 z-50 border-b border-white/10 bg-[#050719]/90 backdrop-blur">
        <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-8">
          <div className="flex items-center">
  <img
    src={careerPilotLogo}
    alt="CareerPilot logo"
    className="h-30 w-auto object-contain"
  />
</div>

          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-950/40 transition hover:scale-[1.02]"
          >
            Sign in
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto flex min-h-[calc(100vh-80px)] max-w-7xl flex-col items-center justify-center px-6 py-24 text-center lg:px-8">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300">
            <span className="h-2 w-2 rounded-full bg-indigo-400" />
            Now in private beta — RAG-grounded career agents
          </div>

          <h1 className="max-w-4xl text-6xl font-bold tracking-tight text-white md:text-7xl lg:text-8xl">
            Your career,
            <span className="block bg-gradient-to-r from-blue-500 to-violet-400 bg-clip-text text-transparent">
              on autopilot.
            </span>
          </h1>

          <p className="mt-8 max-w-3xl text-xl leading-9 text-slate-400">
            CareerPilot is the agentic co-pilot that hunts jobs, grounds every
            answer in your real CV, spots your skill gaps, and keeps you
            accountable — all in one place.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-3 rounded-full bg-gradient-to-r from-blue-500 to-violet-500 px-8 py-4 text-lg font-bold text-white shadow-xl shadow-indigo-950/40 transition hover:scale-[1.02]"
            >
              Open the dashboard
              <ArrowRight className="h-5 w-5" />
            </Link>

            <a
              href="#how-it-works"
              className="inline-flex items-center rounded-full border border-white/10 px-8 py-4 text-lg font-bold text-white transition hover:bg-white/5"
            >
              See how it works
            </a>
          </div>

          <p className="mt-8 text-sm text-slate-500">
            Free during beta · No credit card · Drop your CV and go
          </p>
        </section>

        <section className="border-y border-white/10 py-14">
          <div className="mx-auto max-w-7xl px-6 text-center lg:px-8">
            <p className="text-xs font-bold uppercase tracking-[0.4em] text-slate-500">
              Trusted by job seekers targeting
            </p>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-14 gap-y-5 text-sm font-bold uppercase tracking-[0.25em] text-slate-500">
              <span>Stripe</span>
              <span>Linear</span>
              <span>Vercel</span>
              <span>Notion</span>
              <span>Figma</span>
              <span>Ramp</span>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-28 lg:px-8">
          <p className="text-sm font-bold text-indigo-400">The platform</p>

          <h2 className="mt-6 max-w-4xl text-5xl font-bold tracking-tight text-white md:text-6xl">
            One co-pilot. Every part of the job hunt.
          </h2>

          <p className="mt-6 max-w-3xl text-xl leading-8 text-slate-400">
            Six agents, one memory of you. They do not just answer — they work
            for you.
          </p>

          <div className="mt-16 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-3xl border border-white/10 bg-white/[0.03] p-8 transition hover:border-indigo-400/40 hover:bg-white/[0.05]"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/15 text-indigo-400">
                  <feature.icon className="h-6 w-6" strokeWidth={2.2} />
                </div>

                <h3 className="mt-8 text-2xl font-bold text-white">
                  {feature.title}
                </h3>

                <p className="mt-4 text-base leading-7 text-slate-400">
                  {feature.description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-y border-white/10 px-6 py-28 lg:px-8"
        >
          <div className="mx-auto max-w-7xl">
            <p className="text-sm font-bold text-indigo-400">How it works</p>

            <h2 className="mt-6 text-5xl font-bold tracking-tight text-white md:text-6xl">
              From CV to offer in three moves.
            </h2>

            <div className="mt-16 grid gap-6 lg:grid-cols-3">
              {steps.map((step) => (
                <article
                  key={step.number}
                  className="rounded-3xl border border-white/10 bg-white/[0.03] p-10"
                >
                  <p className="text-3xl font-bold text-indigo-400">
                    {step.number}
                  </p>

                  <h3 className="mt-8 text-2xl font-bold text-white">
                    {step.title}
                  </h3>

                  <p className="mt-4 text-base leading-7 text-slate-400">
                    {step.description}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 py-28 lg:px-8">
          <p className="text-sm font-bold text-indigo-400">A glimpse</p>

          <h2 className="mt-6 text-5xl font-bold tracking-tight text-white md:text-6xl">
            Your agent, working in real time.
          </h2>

          <div className="mt-16 rounded-[2rem] border border-white/10 bg-white/[0.03] p-6 shadow-2xl shadow-indigo-950/30">
            <div className="flex items-center gap-3 border-b border-white/10 pb-5">
              <span className="h-3 w-3 rounded-full bg-red-400" />
              <span className="h-3 w-3 rounded-full bg-amber-400" />
              <span className="h-3 w-3 rounded-full bg-emerald-400" />
              <span className="ml-4 text-sm text-slate-400">
                careerpilot.app/dashboard
              </span>
            </div>

            <div className="grid gap-6 p-4 lg:grid-cols-[1.5fr_0.8fr]">
              <div className="rounded-3xl border border-white/10 bg-[#080b1f] p-8">
                <p className="font-bold text-white">Job Hunter Agent</p>

                <div className="mt-8 ml-auto max-w-2xl rounded-full bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-4 text-white">
                  Find me AI internships in Dhaka with strong growth potential.
                </div>

                <div className="mt-6 inline-flex rounded-full bg-white/10 px-6 py-3 text-slate-300">
                  Scanning openings against your CV... ranking by fit.
                </div>

                <div className="mt-6 space-y-4">
                  <MockJob title="Machine Learning Intern" company="Pathao" fit="94%" />
                  <MockJob title="AI Engineer, Applied" company="Brain Station 23" fit="88%" />
                  <MockJob title="Full-Stack Engineer (ML)" company="ShopUp" fit="81%" />
                </div>
              </div>

              <div className="space-y-6">
                <div className="rounded-3xl border border-white/10 bg-[#080b1f] p-8">
                  <p className="text-slate-400">Weekly streak</p>
                  <h3 className="mt-3 text-4xl font-bold text-white">9 days</h3>

                  <div className="mt-6 grid grid-cols-7 gap-2">
                    {Array.from({ length: 7 }).map((_, index) => (
                      <div
                        key={index}
                        className="h-8 rounded-lg bg-indigo-500/70"
                      />
                    ))}
                  </div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-[#080b1f] p-8">
                  <p className="text-slate-400">Roadmap progress</p>
                  <h3 className="mt-3 text-4xl font-bold text-white">62%</h3>

                  <div className="mt-6 h-3 rounded-full bg-white/10">
                    <div className="h-3 w-[62%] rounded-full bg-gradient-to-r from-blue-500 to-violet-500" />
                  </div>

                  <div className="mt-6 space-y-3 text-slate-300">
                    <p className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      System design basics
                    </p>
                    <p className="flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      React Server Components
                    </p>
                    <p className="flex items-center gap-2 text-white">
                      <span className="h-5 w-5 rounded-full border-2 border-indigo-400" />
                      Distributed caching
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="px-6 py-28 lg:px-8">
          <div className="mx-auto max-w-5xl rounded-[2rem] bg-gradient-to-r from-blue-500 to-violet-400 px-8 py-20 text-center shadow-2xl shadow-indigo-950/40">
            <h2 className="text-5xl font-bold tracking-tight text-white md:text-6xl">
              Stop applying. Start landing.
            </h2>

            <p className="mx-auto mt-6 max-w-2xl text-xl leading-8 text-white/85">
              Drop your CV, pick a target, and let your agents do what generic
              tools never could.
            </p>

            <Link
              to="/dashboard"
              className="mt-10 inline-flex items-center gap-3 rounded-full bg-[#050719] px-8 py-4 font-bold text-white transition hover:scale-[1.02]"
            >
              Launch CareerPilot
              <ArrowRight className="h-5 w-5" />
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

function MockJob({
  title,
  company,
  fit,
}: {
  title: string;
  company: string;
  fit: string;
}) {
  return (
    <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <div>
        <h4 className="font-bold text-white">{title}</h4>
        <p className="mt-1 text-sm text-slate-400">{company}</p>
      </div>

      <span className="text-sm font-bold text-indigo-400">{fit} fit</span>
    </div>
  );
}