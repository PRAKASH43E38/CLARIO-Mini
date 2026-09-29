import React, { useEffect, useState } from 'react';
import { OrchestrationAPI } from '../../api/clarioApi';

interface JourneyDashboardProps {
  sessionId: string;
  onBack: () => void;
  onStartNewSession: () => void;
}

const JourneyDashboard: React.FC<JourneyDashboardProps> = ({ sessionId, onBack, onStartNewSession }) => {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStatus();
  }, [sessionId]);

  const loadStatus = async () => {
    try {
      const data = await OrchestrationAPI.getJourneyStatus(sessionId);
      setStatus(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load journey status.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="w-12 h-12 border-4 border-[#58cc02] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-[#f8fafc]">
        <div className="card-duo max-w-md text-center p-8">
          <p className="text-rose-600 font-bold mb-4">{error || 'No journey data available.'}</p>
          <button onClick={onBack} className="btn-duo-secondary px-6 py-2.5 text-xs cursor-pointer">
            ← Go Back
          </button>
        </div>
      </div>
    );
  }

  const levels = status.roadmap?.levels || [];
  const completedLevels = levels.filter((l: any) => l.status === 'COMPLETED');
  const totalLevels = levels.length;
  const progressPct = totalLevels > 0 ? Math.round((completedLevels.length / totalLevels) * 100) : 0;
  const conceptPerfs = status.concept_performances || [];
  const isGoalCompleted = status.current_stage === 'COMPLETE_GOAL' || status.current_stage === 'SESSION_COMPLETED';

  return (
    <div className="min-h-screen px-4 py-8 max-w-3xl mx-auto space-y-8 bg-[#f8fafc]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer"
        >
          ← ROADMAP
        </button>
        <span className="pill-stat pill-green text-xs">
          Stage: {status.current_stage}
        </span>
      </div>

      {/* Hero Card */}
      <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm text-center">
        <div className="w-20 h-20 rounded-3xl bg-[#58cc02] border-b-6 border-[#46a302] text-white text-4xl flex items-center justify-center mx-auto mb-4 shadow-sm">
          {isGoalCompleted ? '🏆' : '📊'}
        </div>
        <h1 className="text-3xl font-black text-slate-900 mb-2">
          {status.roadmap?.topic || 'Your Learning Journey'}
        </h1>
        <p className="text-slate-600 font-medium text-sm">
          {isGoalCompleted
            ? 'All levels and concepts mastered with evidence-based evaluations!'
            : `${completedLevels.length} of ${totalLevels} levels completed • ${progressPct}% mastered`}
        </p>

        {/* Overall progress */}
        <div className="mt-6 max-w-md mx-auto">
          <div className="flex justify-between text-xs font-black mb-2 text-slate-500">
            <span className="uppercase">Roadmap Progress</span>
            <span className="text-[#15803d]">{progressPct}%</span>
          </div>
          <div className="h-4 bg-slate-100 border border-slate-200 rounded-full overflow-hidden p-0.5">
            <div
              className="h-full rounded-full bg-[#58cc02] transition-all duration-700"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-3 gap-3.5">
        <div className="bg-white border-2 border-emerald-100 border-b-4 border-emerald-300 rounded-2xl p-4 text-center">
          <p className="text-2xl font-black text-[#15803d]">{completedLevels.length}</p>
          <p className="text-[11px] font-black uppercase text-slate-500 mt-1">Levels Done</p>
        </div>
        <div className="bg-white border-2 border-orange-100 border-b-4 border-orange-300 rounded-2xl p-4 text-center">
          <p className="text-2xl font-black text-[#c2410c]">{status.remediation_count || 0}</p>
          <p className="text-[11px] font-black uppercase text-slate-500 mt-1">Remediations</p>
        </div>
        <div className="bg-white border-2 border-purple-100 border-b-4 border-purple-300 rounded-2xl p-4 text-center">
          <p className="text-2xl font-black text-[#6d28d9]">{conceptPerfs.length}</p>
          <p className="text-[11px] font-black uppercase text-slate-500 mt-1">Concepts</p>
        </div>
      </div>

      {/* Concept Performances */}
      {conceptPerfs.length > 0 && (
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-4">
          <h2 className="text-base font-black text-slate-900 uppercase tracking-wider">
            Concept Mastery Overview
          </h2>
          <div className="space-y-3">
            {conceptPerfs.map((cp: any) => {
              const score = Math.round((cp.mastery_score || 0) * 100);
              const isHigh = score >= 80;
              return (
                <div key={`${cp.concept}-${cp.level_id}`} className="bg-[#f8fafc] border-2 border-slate-200 rounded-2xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-extrabold text-sm text-slate-800">{cp.concept}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${
                        isHigh ? 'bg-emerald-100 text-emerald-800' : 'bg-orange-100 text-orange-800'
                      }`}>
                        {cp.status}
                      </span>
                      <span className={`font-mono text-xs font-black ${
                        isHigh ? 'text-[#15803d]' : 'text-[#c2410c]'
                      }`}>
                        {score}%
                      </span>
                    </div>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${isHigh ? 'bg-[#58cc02]' : 'bg-[#ff9600]'}`}
                      style={{ width: `${score}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="pt-2 flex gap-4">
        <button
          onClick={onStartNewSession}
          className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
        >
          🚀 START NEW LEARNING JOURNEY
        </button>
      </div>
    </div>
  );
};

export default JourneyDashboard;
