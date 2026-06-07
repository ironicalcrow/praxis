import type { Application, ApplicationStatus } from "../types/applications";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

type FetchApplicationsParams = {
  userId: string;
  status?: ApplicationStatus;
  includeArchived?: boolean;
};

export type KanbanApplications = Record<ApplicationStatus, Application[]>;

export async function fetchApplications({
  userId,
  status,
  includeArchived = false,
}: FetchApplicationsParams): Promise<Application[]> {
  const params = new URLSearchParams({
    user_id: userId,
    include_archived: String(includeArchived),
  });

  if (status) {
    params.set("status", status);
  }

  const response = await fetch(
    `${API_BASE_URL}/api/application/applications?${params.toString()}`
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to fetch applications");
  }

  const data = await response.json();

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.applications)) {
    return data.applications;
  }

  if (Array.isArray(data.data)) {
    return data.data;
  }

  return [];
}

export async function fetchKanbanApplications(
  userId: string
): Promise<KanbanApplications> {
  const params = new URLSearchParams({
    user_id: userId,
  });

  const response = await fetch(
    `${API_BASE_URL}/api/application/applications/kanban?${params.toString()}`
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to fetch Kanban applications");
  }

  return response.json();
}

export async function updateApplicationStatus({
  applicationId,
  userId,
  status,
  reason,
}: {
  applicationId: string;
  userId: string;
  status: ApplicationStatus;
  reason?: string;
}): Promise<Application> {
  const response = await fetch(
    `${API_BASE_URL}/api/application/applications/${applicationId}/status`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        status,
        reason,
      }),
    }
  );

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to update application status");
  }

  return response.json();
}