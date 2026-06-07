// frontend/src/pages/RegisterPage.tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/auth-context";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setInfo("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    try {
      setIsSubmitting(true);
      await register({ name, username, email, password });
      navigate("/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Registration failed";
      // Email-verification case from backend
      if (message.toLowerCase().includes("verify email")) {
        setInfo(message);
      } else {
        setError(message);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#050719] px-6 text-white">
      <div className="w-full max-w-md rounded-3xl border border-white/10 bg-white/[0.03] p-8 shadow-2xl">
        <h1 className="text-3xl font-bold tracking-tight">Create your account</h1>
        <p className="mt-2 text-slate-400">Start your CareerPilot journey.</p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
          <Field label="Full name" value={name} onChange={setName} placeholder="Jane Doe" />
          <Field label="Username" value={username} onChange={setUsername} placeholder="janedoe" />
          <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="jane@example.com" />
          <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="At least 8 characters" />

          {error && (
            <div className="rounded-2xl border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-300">
              {error}
            </div>
          )}
          {info && (
            <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
              {info}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-2xl bg-gradient-to-r from-blue-500 to-violet-500 px-6 py-3 font-bold text-white transition hover:opacity-95 disabled:opacity-60"
          >
            {isSubmitting ? "Creating account..." : "Sign up"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-400">
          Already have an account?{" "}
          <Link to="/login" className="font-semibold text-indigo-400">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-slate-300">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
        className="w-full rounded-xl border border-white/10 bg-[#080b1f] px-4 py-3 text-white outline-none transition focus:border-indigo-400"
      />
    </div>
  );
}