import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  {
    label: "Job Search",
    href: "/",
  },
  {
    label: "CV Extraction",
    href: "/cv",
  },
];

export default function AppLayout() {
  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/90 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <h1 className="text-lg font-bold text-white">CareerPilot</h1>

          <nav className="flex gap-2">
            {navItems.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                className={({ isActive }) =>
                  [
                    "rounded-xl px-4 py-2 text-sm font-semibold transition",
                    isActive
                      ? "bg-blue-600 text-white"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white",
                  ].join(" ")
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <Outlet />
    </div>
  );
}