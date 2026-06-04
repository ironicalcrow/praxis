import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  BriefcaseBusiness,
  FileText,
  MessageSquare,
  CalendarDays,
  Goal,
  Settings,
  Bell,
} from "lucide-react";
import careerPilotLogo from "../assets/CareerPilot Logo.png";

const navItems = [
  {
    label: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Job Hunter",
    href: "/jobs",
    icon: BriefcaseBusiness,
  },
  {
    label: "My CV",
    href: "/cv",
    icon: FileText,
  },
  {
    label: "AI Assistant",
    href: "/assistant",
    icon: MessageSquare,
  },
  {
    label: "Calendar",
    href: "/calendar",
    icon: CalendarDays,
  },
  {
    label: "Goals",
    href: "/goals",
    icon: Goal,
  },
];

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f8ff] text-slate-950">
      <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white px-2 py-4 lg:flex lg:flex-col">
        <div className="mb-4 h-28 overflow-hidden">
          <img
            src={careerPilotLogo}
            alt="CareerPilot logo"
            className="h-36 w-auto -translate-y-4 object-contain"
          />
        </div>

        <nav className="flex flex-1 flex-col items-center gap-3">
          {navItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                [
                  "flex w-[230px] items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-semibold transition",
                  isActive
                    ? "bg-indigo-50 text-indigo-600"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
                ].join(" ")
              }
            >
              <item.icon className="h-5 w-5 shrink-0" strokeWidth={2.2} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <NavLink
          to="/settings"
          className={({ isActive }) =>
            [
              "mx-auto flex w-[230px] items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-semibold transition",
              isActive
                ? "bg-indigo-50 text-indigo-600"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
            ].join(" ")
          }
        >
          <Settings className="h-5 w-5 shrink-0" strokeWidth={2.2} />
          <span>Settings</span>
        </NavLink>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-24 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-6 lg:px-10">
          <div>
            <p className="text-sm font-medium text-slate-500">Welcome back</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">
              Good morning, X
            </h1>
          </div>

          <div className="flex items-center gap-4">
            <button
              type="button"
              className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <Bell className="h-5 w-5 text-slate-500" strokeWidth={2.2} />
            </button>

            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-600 font-bold text-white shadow-sm">
              T
            </div>
          </div>
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}