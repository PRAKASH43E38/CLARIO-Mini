import React, { useState } from 'react';

export interface AuthFormData {
  email: string;
  password: string;
  name: string;
}

export interface AuthResult {
  user_id: string;
  email: string;
  name: string;
  mind_profile_completed: boolean;
}

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function isAuthResult(value: unknown): value is AuthResult {
  if (typeof value !== "object" || value === null) return false;
  const result = value as Record<string, unknown>;
  return typeof result.user_id === "string"
    && typeof result.email === "string"
    && typeof result.name === "string"
    && typeof result.mind_profile_completed === "boolean";
}

export const AuthPage: React.FC<{
  mode: "register" | "login";
  onComplete: (user: AuthResult) => void;
  onSwitchMode: () => void;
}> = ({ mode, onComplete, onSwitchMode }) => {
  const [form, setForm] = useState<AuthFormData>({ email: "", password: "", name: "" });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          ...(mode === "register" ? { name: form.name } : {}),
        }),
      });
      const data: unknown = await res.json();
      if (!res.ok) {
        const detail =
          typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string"
            ? data.detail
            : "Something went wrong.";
        setError(detail);
        return;
      }
      if (!isAuthResult(data)) {
        setError("The server returned invalid account information.");
        return;
      }
      onComplete(data);
    } catch {
      setError("Could not reach the server. Is the backend running?");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="w-16 h-16 rounded-2xl bg-[#58cc02] border-b-4 border-[#46a302] flex items-center justify-center text-3xl text-white shadow-sm mb-3">
            🌱
          </div>
          <h2 className="text-3xl font-black text-slate-900 tracking-tight">CLARIO</h2>
          <p className="text-xs font-bold text-slate-500 mt-1 uppercase tracking-wider">
            Autonomous Adaptive Learning
          </p>
        </div>

        {/* 3D Card */}
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
          <h1 className="text-2xl font-black text-slate-900 mb-6 text-center">
            {mode === "register" ? "Create your profile" : "Welcome back!"}
          </h1>

          {error && (
            <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-3 mb-5 text-xs text-rose-700 font-bold flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={submit} className="space-y-4">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 mb-1.5">
                  Display name
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition"
                  placeholder="e.g. Alex Rivera"
                  required
                  maxLength={100}
                />
              </div>
            )}

            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition"
                placeholder="At least 8 characters"
                required
                minLength={8}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="btn-duo-green w-full py-4 mt-2 text-sm tracking-wider cursor-pointer"
            >
              {submitting ? "PLEASE WAIT..." : mode === "register" ? "CREATE ACCOUNT" : "LOG IN"}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t-2 border-slate-100 text-center">
            <p className="text-xs text-slate-500 font-bold">
              {mode === "register" ? "Already have an account? " : "New to CLARIO? "}
              <button
                type="button"
                className="text-[#46a302] hover:text-[#58cc02] font-black underline cursor-pointer ml-1"
                onClick={onSwitchMode}
              >
                {mode === "register" ? "Log in" : "Create one"}
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
