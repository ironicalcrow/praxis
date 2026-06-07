// frontend/src/auth/ProtectedRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./auth-context";

export default function ProtectedRoute() {
  const { token, isLoading } = useAuth();
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f8ff] text-slate-500">
        Loading...
      </div>
    );
  }
  return token ? <Outlet /> : <Navigate to="/login" replace />;
}