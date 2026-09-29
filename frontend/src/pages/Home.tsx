import React, { useState, useEffect } from 'react';
import { SessionAPI } from '../api/sessionApi';

export const Home: React.FC<{
  user: { user_id: string; email: string; name: string };
  onLogout: () => void;
  onEditProfile: () => void;
  onEditMindProfile: () => void;
  onStartLearning: (sessionId: string) => void;
  onResumeSession: (sessionId: string) => void;
}> = ({ user, onEditProfile, onEditMindProfile, onStartLearning, onResumeSession }) => {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    loadSessions();
  }, [user.user_id]);

  const loadSessions = async () => {
    setFetching(true);
    try {
      const data = await SessionAPI.listSessions(user.user_id);
      setSessions(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Failed to load sessions', err);
      setSessions([]);
    } finally {
      setFetching(false);
    }
  };

  const handleStartLearning = async () => {
    setLoading(true);
    try {
      const session = await SessionAPI.createSession();
      onStartLearning(session.session_id);
    } catch (err) {
      alert('Failed to start learning session.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-10 px-4 space-y-8">
      {/* Welcome Hero Card */}
      <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm text-center relative overflow-hidden">
        <div className="inline-flex items-center justify-center w-18 h-18 rounded-3xl bg-[#58cc02] border-b-4 border-[#46a302] text-white text-3xl mb-4 shadow-sm">
          🌱
        </div>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
          Welcome back, {user.name}!
        </h1>
        <p className="text-slate-600 font-medium max-w-lg mx-auto mb-8 text-sm md:text-base leading-relaxed">
          Your Mind Profile is loaded. Ready to master a new topic with CLARIO-AI and the 6 agents?
        </p>

        <div className="flex flex-col items-center gap-4 mb-6">
          <button
            onClick={handleStartLearning}
            disabled={loading}
            className="btn-duo-green w-full sm:w-80 py-4 text-base tracking-wider shadow-sm cursor-pointer"
          >
            {loading ? 'CREATING SESSION...' : '🚀 START NEW TOPIC'}
          </button>
        </div>

        {/* Quick preference actions */}
        <div className="flex flex-wrap justify-center gap-3 pt-2 border-t-2 border-slate-100">
          <button
            onClick={onEditMindProfile}
            className="btn-duo-secondary px-4 py-2.5 text-xs cursor-pointer flex items-center gap-1.5"
          >
            <span>🧠</span>
            <span>Update Mind Preferences</span>
          </button>
          <button
            onClick={onEditProfile}
            className="btn-duo-secondary px-4 py-2.5 text-xs cursor-pointer flex items-center gap-1.5"
          >
            <span>👤</span>
            <span>Edit Display Name</span>
          </button>
        </div>
      </div>

      {/* Learning Sessions Section */}
      <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-xl bg-emerald-100 text-[#15803d] font-black text-sm flex items-center justify-center">
              📚
            </span>
            <h2 className="text-xl font-black text-slate-900">Your Learning Journeys</h2>
          </div>
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Real Database Records
          </span>
        </div>

        {fetching ? (
          <div className="text-center py-12">
            <div className="w-10 h-10 border-4 border-[#58cc02] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs font-bold text-slate-400">Loading your learning history...</p>
          </div>
        ) : sessions.length === 0 ? (
          /* Clean Real Empty State */
          <div className="text-center py-12 px-4 rounded-2xl bg-[#f8fafc] border-2 border-dashed border-slate-200">
            <div className="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 text-3xl flex items-center justify-center mx-auto mb-3">
              ✨
            </div>
            <h3 className="text-lg font-black text-slate-800">No learning sessions yet</h3>
            <p className="text-xs text-slate-500 font-medium max-w-md mx-auto mt-1 mb-5">
              Welcome to CLARIO! Click &quot;Start New Topic&quot; above to specify your goal and interest. CALA will construct your personalized autonomous roadmap.
            </p>
            <button
              onClick={handleStartLearning}
              disabled={loading}
              className="btn-duo-green px-6 py-2.5 text-xs tracking-wider cursor-pointer"
            >
              START FIRST TOPIC →
            </button>
          </div>
        ) : (
          <div className="space-y-3.5">
            {sessions.map((s) => {
              const isReady = s.status === 'READY_FOR_CALA' || s.status === 'IN_PROGRESS' || s.status === 'GOAL_COMPLETED';
              return (
                <div
                  key={s.session_id}
                  onClick={() => isReady ? onResumeSession(s.session_id) : onStartLearning(s.session_id)}
                  className="p-5 rounded-2xl border-2 border-slate-200/90 hover:border-[#58cc02] hover:bg-[#f0fdf4]/30 cursor-pointer transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs"
                >
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 flex items-center justify-center text-xl shrink-0">
                      {s.status === 'GOAL_COMPLETED' ? '🏆' : '🗺️'}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-slate-900 text-base">
                          {s.task || `Session ${s.session_id.slice(0, 8)}`}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 font-medium mt-0.5">
                        {isReady ? 'Active autonomous learning path' : 'Session inputs incomplete'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-3 py-1 rounded-full font-black border ${
                      s.status === 'GOAL_COMPLETED'
                        ? 'bg-purple-100 text-purple-800 border-purple-200'
                        : isReady
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                          : 'bg-amber-100 text-amber-800 border-amber-200'
                    }`}>
                      {s.status === 'GOAL_COMPLETED' ? '✓ Mastered' : isReady ? 'In Progress' : 'Draft'}
                    </span>
                    <span className="text-xs font-bold text-[#46a302] hidden sm:inline">
                      {isReady ? 'Resume →' : 'Continue →'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
