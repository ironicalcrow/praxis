export type JobSearchRequest = {
  query: string;
  location: string;
  page: number;
  num_pages: number;
};

export type JobCardType = {
  title: string;
  company: string;
  location: string;
  employment_type?: string | null;
  salary_range?: string | null;
  description?: string | null;
  job_url?: string | null;
  source?: string | null;
  posted_at?: string | null;
};