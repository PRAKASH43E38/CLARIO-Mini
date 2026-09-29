import React, { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function errorMessage(payload: unknown, fallback: string): string {
  if (
    typeof payload === 'object'
    && payload !== null
    && 'detail' in payload
    && typeof payload.detail === 'string'
  ) {
    return payload.detail;
  }
  return fallback;
}

export const ProfileSetup: React.FC<{
  user: { user_id: string; email: string; name: string };
  onComplete: (name: string) => void;
}> = ({ user, onComplete }) => {
  const [name, setName] = useState(user.name);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${API}/profile/${encodeURIComponent(user.user_id)}`, {
      credentials: 'include',
    })
      .then(async (response) => {
        const data: unknown = await response.json();
        if (!response.ok) throw new Error(errorMessage(data, 'Could not load your profile.'));
        if (typeof data !== 'object' || data === null || !('name' in data) || typeof data.name !== 'string') {
          throw new Error('The server returned invalid profile information.');
        }
        return { name: data.name };
      })
      .then((profile) => {
        if (active) setName(profile.name);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Could not load your profile.');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [user.user_id]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const response = await fetch(`${API}/profile/${encodeURIComponent(user.user_id)}`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() }),
      });
      const data: unknown = await response.json();
      if (!response.ok) throw new Error(errorMessage(data, 'Could not save your profile.'));
      if (typeof data !== 'object' || data === null || !('name' in data) || typeof data.name !== 'string') {
        throw new Error('The server returned invalid profile information.');
      }
      onComplete(data.name);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save your profile.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <div className="w-16 h-16 rounded-2xl bg-[#58cc02] border-b-4 border-[#46a302] flex items-center justify-center text-3xl text-white shadow-sm mb-3">
            👤
          </div>
          <h2 className="text-2xl font-black text-slate-900 tracking-tight">Set up your profile</h2>
          <p className="text-xs font-bold text-slate-500 mt-1 uppercase tracking-wider">
            Step 1 • Learner Identity
          </p>
        </div>

        {/* 3D Card */}
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
          <p className="text-sm text-slate-600 font-medium mb-6">
            Choose how you would like CLARIO and the 6 agents to address you throughout your personalized journey.
          </p>

          {error && (
            <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-3 mb-5 text-xs text-rose-700 font-bold flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label htmlFor="profile-name" className="block text-xs font-extrabold uppercase tracking-wider text-slate-600 mb-1.5">
                Full Name or Display Name
              </label>
              <input
                id="profile-name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition"
                placeholder="e.g. Maya Lin"
                autoFocus
                required
                minLength={1}
                maxLength={100}
              />
            </div>

            <button
              type="submit"
              disabled={loading || saving || !name.trim()}
              className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
            >
              {loading ? 'LOADING...' : saving ? 'SAVING...' : 'CONTINUE →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
