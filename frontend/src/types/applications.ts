export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected";

export type Application = {
  id: string;
  user_id: string;
  job_id?: string | null;

  job_title: string;
  company: string;
  location?: string | null;
  apply_url?: string | null;
  source?: string | null;
  salary?: string | null;

  status: ApplicationStatus;
  applied_at?: string | null;
  last_status_changed_at?: string | null;

  is_archived: boolean;

  created_at?: string | null;
  updated_at?: string | null;

  notes?: unknown[];
  status_history?: unknown[];
};