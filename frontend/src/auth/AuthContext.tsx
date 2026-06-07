// frontend/src/auth/AuthContext.tsx
import { useEffect, useState } from "react";
import {
  fetchMe,
  loginUser,
  logoutUser,
  registerUser,
  type UserResponse,
  type LoginPayload,
  type RegisterPayload,
} from "../api/auth";
import { AuthContext, ACCESS_KEY, REFRESH_KEY } from "./auth-context";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem(ACCESS_KEY)
  );
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function hydrate() {
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        setUser(await fetchMe(token));
      } catch {
        localStorage.removeItem(ACCESS_KEY);
        localStorage.removeItem(REFRESH_KEY);
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    hydrate();
  }, [token]);

  function persist(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
    setToken(access);
  }

  async function login(payload: LoginPayload) {
    const res = await loginUser(payload);
    persist(res.access_token, res.refresh_token);
    setUser(await fetchMe(res.access_token));
  }

  async function register(payload: RegisterPayload) {
    const res = await registerUser(payload);
    persist(res.access_token, res.refresh_token);
    setUser(await fetchMe(res.access_token));
  }

  async function logout() {
    if (token) await logoutUser(token).catch(() => {});
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, token, isLoading, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}