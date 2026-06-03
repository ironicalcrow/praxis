import type { ResumeData, UploadCvResponse } from "../types/cv";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export async function uploadCv(file: File): Promise<ResumeData> {
  const formData = new FormData();

  /**
   * Backend expects:
   * async def upload_cv(file: UploadFile = File(...))
   *
   * So the field name must be exactly "file".
   */
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/api/cv/upload-cv`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);

    const message =
      errorData?.detail || "Failed to upload and extract CV";

    throw new Error(message);
  }

  const data = (await response.json()) as UploadCvResponse;

  if (!data.success) {
    throw new Error("CV extraction failed");
  }

  return data.data;
}