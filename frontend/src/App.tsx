import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import CvUploadPage from "./pages/CvUploadPage";
import DashboardPage from "./pages/DashboardPage";
import JobSearchPage from "./pages/JobSearchPage";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-6 lg:p-10">
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-indigo-600">
          Coming soon
        </p>
        <h2 className="mt-2 text-3xl font-bold">{title}</h2>
        <p className="mt-3 text-slate-500">
          This section is a UI placeholder for now.
        </p>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/jobs" element={<JobSearchPage />} />
          <Route path="/cv" element={<CvUploadPage />} />
          <Route path="/assistant" element={<PlaceholderPage title="AI Assistant" />} />
          <Route path="/calendar" element={<PlaceholderPage title="Calendar" />} />
          <Route path="/goals" element={<PlaceholderPage title="Goals" />} />
          <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;