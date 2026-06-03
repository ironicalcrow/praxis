import { useState } from "react";
import { uploadCv } from "../api/cv";
import type { ResumeData } from "../types/cv";

const allowedTypes = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/png",
  "image/jpeg",
];

function isAllowedFile(file: File) {
  return allowedTypes.includes(file.type);
}

export default function CvUploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeData, setResumeData] = useState<ResumeData | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    setErrorMessage("");
    setResumeData(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    if (!isAllowedFile(file)) {
      setSelectedFile(null);
      setErrorMessage("Please upload a PDF, DOCX, PNG, JPG, or JPEG file.");
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setErrorMessage("Please select a CV file first.");
      return;
    }

    try {
      setIsUploading(true);
      setErrorMessage("");

      const extractedResume = await uploadCv(selectedFile);

      setResumeData(extractedResume);

      /**
       * Save parsed resume locally for later frontend features:
       * fit score, assistant context preview, dashboard, etc.
       */
      localStorage.setItem(
        "careerpilot_resume",
        JSON.stringify(extractedResume)
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Something went wrong";

      setErrorMessage(message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-8 text-white">
      <div className="mx-auto max-w-6xl">
        <section className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-400">
            CareerPilot
          </p>

          <h1 className="mt-2 text-4xl font-bold">CV Extraction</h1>

          <p className="mt-3 max-w-2xl text-slate-400">
            Upload a resume file and extract structured profile information
            using the FastAPI CV parser.
          </p>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
          <label className="mb-3 block text-sm font-semibold text-slate-300">
            Upload CV
          </label>

          <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-6">
            <input
              type="file"
              accept=".pdf,.docx,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="block w-full cursor-pointer rounded-xl border border-slate-700 bg-slate-900 text-sm text-slate-300 file:mr-4 file:cursor-pointer file:border-0 file:bg-blue-600 file:px-4 file:py-3 file:font-semibold file:text-white hover:file:bg-blue-500"
            />

            <p className="mt-3 text-sm text-slate-500">
              Supported formats: PDF, DOCX, PNG, JPG, JPEG.
            </p>

            {selectedFile && (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                <p className="text-sm text-slate-400">Selected file</p>
                <p className="mt-1 font-semibold text-white">
                  {selectedFile.name}
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleUpload}
            disabled={isUploading || !selectedFile}
            className="mt-5 rounded-xl bg-blue-600 px-5 py-3 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          >
            {isUploading ? "Extracting CV..." : "Extract CV"}
          </button>

          {errorMessage && (
            <div className="mt-6 rounded-xl border border-red-800 bg-red-950 p-4 text-red-200">
              <p className="font-semibold">Something went wrong</p>
              <p className="mt-1 text-sm">{errorMessage}</p>
            </div>
          )}
        </section>

        {resumeData && <ResumePreview resume={resumeData} />}
      </div>
    </main>
  );
}

function ResumePreview({ resume }: { resume: ResumeData }) {
  return (
    <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
      <div className="mb-6 flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-emerald-400">
            Extraction complete
          </p>

          <h2 className="mt-2 text-3xl font-bold text-white">
            {resume.name || "Unnamed Candidate"}
          </h2>

          <p className="mt-2 text-slate-400">
            {resume.email || "No email found"}
            {resume.phone ? ` • ${resume.phone}` : ""}
          </p>

          {resume.location && (
            <p className="mt-1 text-slate-400">{resume.location}</p>
          )}
        </div>

        <div className="rounded-xl bg-slate-950 px-4 py-3 text-sm text-slate-300">
          Experience:{" "}
          <span className="font-bold text-white">
            {resume.years_of_experience ?? 0}
          </span>{" "}
          years
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <InfoCard title="Skills">
          {resume.skills.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {resume.skills.map((skill) => (
                <span
                  key={skill}
                  className="rounded-full bg-blue-950 px-3 py-1 text-sm text-blue-300"
                >
                  {skill}
                </span>
              ))}
            </div>
          ) : (
            <EmptyText text="No skills found." />
          )}
        </InfoCard>

        <InfoCard title="Certifications">
          {resume.certifications.length > 0 ? (
            <ul className="space-y-2 text-sm text-slate-300">
              {resume.certifications.map((certification) => (
                <li key={certification}>• {certification}</li>
              ))}
            </ul>
          ) : (
            <EmptyText text="No certifications found." />
          )}
        </InfoCard>

        <InfoCard title="Education">
          {resume.education.length > 0 ? (
            <div className="space-y-4">
              {resume.education.map((education, index) => (
                <div
                  key={`${education.degree}-${index}`}
                  className="rounded-xl bg-slate-950 p-4"
                >
                  <h3 className="font-bold text-white">
                    {education.degree || "Degree not found"}
                  </h3>
                  <p className="mt-1 text-sm text-slate-300">
                    {education.institution || "Institution not found"}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {education.year || "Year not found"}
                    {education.gpa ? ` • GPA: ${education.gpa}` : ""}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <EmptyText text="No education found." />
          )}
        </InfoCard>

        <InfoCard title="Experience">
          {resume.experience.length > 0 ? (
            <div className="space-y-4">
              {resume.experience.map((experience, index) => (
                <div
                  key={`${experience.role}-${index}`}
                  className="rounded-xl bg-slate-950 p-4"
                >
                  <h3 className="font-bold text-white">
                    {experience.role || "Role not found"}
                  </h3>
                  <p className="mt-1 text-sm text-slate-300">
                    {experience.organization || "Organization not found"}
                  </p>
                  {experience.description && (
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {experience.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyText text="No experience found." />
          )}
        </InfoCard>

        <InfoCard title="Projects">
          {resume.projects.length > 0 ? (
            <div className="space-y-4">
              {resume.projects.map((project, index) => (
                <div
                  key={`${project.name}-${index}`}
                  className="rounded-xl bg-slate-950 p-4"
                >
                  <h3 className="font-bold text-white">
                    {project.name || "Project name not found"}
                  </h3>
                  {project.description && (
                    <p className="mt-2 text-sm leading-6 text-slate-400">
                      {project.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyText text="No projects found." />
          )}
        </InfoCard>

        <InfoCard title="Raw Text">
          {resume.raw_text ? (
            <p className="max-h-80 overflow-y-auto whitespace-pre-wrap text-sm leading-6 text-slate-400">
              {resume.raw_text}
            </p>
          ) : (
            <EmptyText text="No raw text returned." />
          )}
        </InfoCard>
      </div>
    </section>
  );
}

function InfoCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-5">
      <h2 className="mb-4 text-xl font-bold text-white">{title}</h2>
      {children}
    </div>
  );
}

function EmptyText({ text }: { text: string }) {
  return <p className="text-sm text-slate-500">{text}</p>;
}