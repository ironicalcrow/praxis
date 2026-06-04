import { useState } from "react";
import { uploadCv } from "../api/cv";
import type { ResumeData } from "../types/cv";
import { Upload } from "lucide-react";

export default function CvUploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [resumeData, setResumeData] = useState<ResumeData | null>(() => {
    const saved = localStorage.getItem("careerpilot_resume");
    return saved ? JSON.parse(saved) : null;
  });
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    setErrorMessage("");

    if (!file) {
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setErrorMessage("Please select a CV first.");
      return;
    }

    try {
      setIsUploading(true);
      setErrorMessage("");

      const extractedResume = await uploadCv(selectedFile);

      setResumeData(extractedResume);
      localStorage.setItem("careerpilot_resume", JSON.stringify(extractedResume));
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-7xl p-6 lg:p-10">
      <section className="mb-8">
        <p className="text-sm font-bold uppercase tracking-wide text-indigo-600">
          CareerPilot
        </p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">My CV</h1>
        <p className="mt-3 max-w-2xl text-slate-500">
          Upload your resume and extract structured profile information for downstream agents.
        </p>
      </section>

      <section className="grid gap-7 xl:grid-cols-[0.85fr_1.15fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          <div className="rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50 p-8 text-center">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-500 shadow-md">
  <Upload className="h-10 w-10 text-white" strokeWidth={2.2} />
</div>
            <h2 className="mt-6 text-2xl font-bold">Upload your CV</h2>
            <p className="mx-auto mt-3 max-w-sm text-slate-500">
              PDF, DOCX, PNG, JPG, or JPEG. Your CV becomes the source of truth for CareerPilot.
            </p>

            <label className="mt-7 inline-flex cursor-pointer items-center gap-3 rounded-2xl bg-indigo-600 px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-indigo-500">
  <Upload className="h-5 w-5" strokeWidth={2.4} />
  Choose file
  <input
    type="file"
    accept=".pdf,.docx,.png,.jpg,.jpeg"
    className="hidden"
    onChange={handleFileChange}
  />
</label>
          </div>

          {selectedFile && (
            <div className="mt-5 rounded-3xl border border-slate-200 bg-white p-5">
              <p className="text-sm font-semibold text-slate-500">Selected file</p>
              <p className="mt-1 font-bold">{selectedFile.name}</p>
              <p className="mt-1 text-sm text-slate-500">
                {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={isUploading || !selectedFile}
            className="mt-5 w-full rounded-2xl bg-indigo-600 px-6 py-4 font-semibold text-white shadow-sm hover:bg-indigo-500 disabled:bg-slate-300"
          >
            {isUploading ? "Extracting CV..." : "Extract CV"}
          </button>

          {errorMessage && (
            <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {errorMessage}
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-7 shadow-sm">
          {!resumeData ? (
            <div className="flex min-h-[420px] items-center justify-center rounded-3xl bg-slate-50 p-8 text-center">
              <div>
                <p className="text-sm font-bold uppercase tracking-wide text-slate-400">
                  No CV parsed yet
                </p>
                <h2 className="mt-2 text-3xl font-bold">Your profile will appear here</h2>
                <p className="mx-auto mt-3 max-w-md text-slate-500">
                  Upload and extract a CV to view skills, education, projects, and experience.
                </p>
              </div>
            </div>
          ) : (
            <ResumePreview resume={resumeData} />
          )}
        </div>
      </section>
    </div>
  );
}

function ResumePreview({ resume }: { resume: ResumeData }) {
  return (
    <div>
      <div className="border-b border-slate-200 pb-6">
        <p className="text-sm font-bold uppercase tracking-wide text-emerald-600">
          Extraction complete
        </p>
        <h2 className="mt-2 text-3xl font-bold">
          {resume.name || "Unnamed Candidate"}
        </h2>
        <p className="mt-2 text-slate-500">
          {resume.email || "No email found"}
          {resume.phone ? ` • ${resume.phone}` : ""}
        </p>
        {resume.location && <p className="mt-1 text-slate-500">{resume.location}</p>}
      </div>

      <Section title="Skills">
        <div className="flex flex-wrap gap-2">
          {(resume.skills || []).map((skill) => (
            <span
              key={skill}
              className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-medium text-indigo-600"
            >
              {skill}
            </span>
          ))}
        </div>
      </Section>

      <Section title="Education">
        <div className="space-y-3">
          {(resume.education || []).map((item, index) => (
            <InfoBlock key={index} title={item.degree} subtitle={item.institution} text={item.year} />
          ))}
        </div>
      </Section>

      <Section title="Experience">
        <div className="space-y-3">
          {(resume.experience || []).map((item, index) => (
            <InfoBlock
              key={index}
              title={item.role}
              subtitle={item.organization}
              text={item.description}
            />
          ))}
        </div>
      </Section>

      <Section title="Projects">
        <div className="space-y-3">
          {(resume.projects || []).map((item, index) => (
            <InfoBlock key={index} title={item.name} text={item.description} />
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-7">
      <h3 className="mb-3 text-lg font-bold">{title}</h3>
      {children}
    </section>
  );
}

function InfoBlock({
  title,
  subtitle,
  text,
}: {
  title?: string | null;
  subtitle?: string | null;
  text?: string | null;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <h4 className="font-bold">{title || "Not found"}</h4>
      {subtitle && <p className="mt-1 text-sm text-slate-600">{subtitle}</p>}
      {text && <p className="mt-2 text-sm leading-6 text-slate-500">{text}</p>}
    </div>
  );
}