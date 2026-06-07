import { createContext, useContext } from "react";
import type { UserResponse, LoginPayload, RegisterPayload } from "../api/auth";

export type AuthContextType = {
  user: UserResponse | null;
  token: string | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
};

export const ACCESS_KEY = "careerpilot_access_token";
export const REFRESH_KEY = "careerpilot_refresh_token";

export const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function getStoredToken() {
  return localStorage.getItem(ACCESS_KEY);
}