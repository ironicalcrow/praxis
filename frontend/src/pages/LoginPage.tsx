// frontend/src/pages/LoginPage.tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/auth-context";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    try {
      setIsSubmitting(true);
      await login({ email, password });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#050719] px-6 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/[0.03] p-8 shadow-2xl">
        <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
        <p className="mt-2 text-slate-400">Sign in to continue.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-xl border border-white/10 bg-[#080b1f] px-4 py-3 text-white outline-none focus:border-indigo-400"
            />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-300">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-xl border border-white/10 bg-[#080b1f] px-4 py-3 text-white outline-none focus:border-indigo-400"
            />
          </div>

          {error && (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-3 font-bold text-white transition hover:opacity-95 disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          No account?{" "}
          <Link to="/register" className="font-semibold text-indigo-400">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}