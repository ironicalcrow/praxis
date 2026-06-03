import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import CvUploadPage from "./pages/CvUploadPage";
import JobSearchPage from "./pages/JobSearchPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<JobSearchPage />} />
          <Route path="/cv" element={<CvUploadPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;