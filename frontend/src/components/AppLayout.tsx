import { NavLink, Outlet } from "react-router-dom";
import careerPilotLogo from "../assets/CareerPilot Logo.png";

const navItems = [
  {
    label: "Dashboard",
    href: "/",
    icon: "▦",
  },
  {
    label: "Job Hunter",
    href: "/jobs",
    icon: "▣",
  },
  {
    label: "My CV",
    href: "/cv",
    icon: "▤",
  },
  {
    label: "AI Assistant",
    href: "/assistant",
    icon: "□",
  },
  {
    label: "Calendar",
    href: "/calendar",
    icon: "◷",
  },
  {
    label: "Goals",
    href: "/goals",
    icon: "◎",
  },
];

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-[#f5f8ff] text-slate-950">
      <aside className="hidden w-72 shrink-0 border-r border-slate-200 bg-white px-2 py-4 lg:flex lg:flex-col">
        <div className="mb-10">
  <img
    src={careerPilotLogo}
    alt="CareerPilot logo"
    className="h-40 w-auto object-contain"
  />
</div>
        <nav className="flex flex-1 flex-col gap-2">
          {navItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition",
                  isActive
                    ? "bg-indigo-50 text-indigo-600"
                    : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
                ].join(" ")
              }
            >
              <span className="text-lg">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <NavLink
          to="/settings"
          className="flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold text-slate-500 hover:bg-slate-50 hover:text-slate-900"
        >
          <span className="text-lg">⚙</span>
          Settings
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
              className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-200 bg-white text-xl shadow-sm"
            >
              🔔
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