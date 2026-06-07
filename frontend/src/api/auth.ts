// frontend/src/api/auth.ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};

export type UserResponse = {
  id: string;
  email: string;
  name?: string | null;
  username?: string | null;
};

export type RegisterPayload = {
  name: string;
  username: string;
  email: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    throw new Error(data?.detail || "Request failed");
  }
  return res.json();
}

export async function registerUser(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle<AuthResponse>(res);
}

export async function loginUser(payload: LoginPayload): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle<AuthResponse>(res);
}

export async function fetchMe(token: string): Promise<UserResponse> {
  const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return handle<UserResponse>(res);
}

export async function logoutUser(token: string): Promise<void> {
  await fetch(`${API_BASE_URL}/api/auth/logout`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}