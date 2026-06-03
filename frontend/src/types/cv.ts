export type Education = {
  degree?: string | null;
  institution?: string | null;
  year?: string | null;
  gpa?: string | null;
};

export type Experience = {
  role?: string | null;
  organization?: string | null;
  description?: string | null;
};

export type Project = {
  name?: string | null;
  description?: string | null;
};

export type ResumeData = {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  skills: string[];
  education: Education[];
  experience: Experience[];
  projects: Project[];
  certifications: string[];
  years_of_experience?: number | null;
  raw_text?: string | null;
};

export type UploadCvResponse = {
  success: boolean;
  data: ResumeData;
};