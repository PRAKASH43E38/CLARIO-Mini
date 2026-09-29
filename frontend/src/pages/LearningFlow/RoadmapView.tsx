import React, { useEffect, useState } from 'react';
import { OrchestrationAPI } from '../../api/clarioApi';

interface RoadmapLevel {
  level_id: string;
  level_number: number;
  title: string;
  objective: string;
  difficulty: string;
  status: string;
}

interface RoadmapViewProps {
  sessionId: string;
  userId: string;
  onBack: () => void;
  onEnterLevel: (levelId: string, sessionId: string, level: RoadmapLevel) => void;
}

const RoadmapView: React.FC<RoadmapViewProps> = ({ sessionId, onBack, onEnterLevel }) => {
  const [levels, setLevels] = useState<RoadmapLevel[]>([]);
  const [topic, setTopic] = useState('');
  const [loading, setLoading] = useState(true);
  const [initializing, setInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStage, setCurrentStage] = useState('');

  useEffect(() => {
    initializeAndLoad();
  }, [sessionId]);

  const initializeAndLoad = async () => {
    setLoading(true);
    setError(null);
    try {
      let status = await OrchestrationAPI.getJourneyStatus(sessionId);

      if (status.current_stage === 'NOT_STARTED' || !status.roadmap?.levels?.length) {
        setInitializing(true);
        await OrchestrationAPI.initializeLoop(sessionId);
        setInitializing(false);
        status = await OrchestrationAPI.getJourneyStatus(sessionId);
      }

      setTopic(status.roadmap?.topic || 'Your Learning Journey');
      setCurrentStage(status.current_stage);
      setLevels(status.roadmap?.levels || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to load roadmap.');
    } finally {
      setLoading(false);
      setInitializing(false);
    }
  };

  const completedCount = levels.filter((l) => l.status === 'COMPLETED').length;
  const progressPercent = levels.length > 0 ? Math.round((completedCount / levels.length) * 100) : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-[#f8fafc]">
        <div className="text-center space-y-4 max-w-md">
          <div className="w-16 h-16 rounded-3xl bg-[#58cc02] border-b-4 border-[#46a302] flex items-center justify-center text-3xl text-white shadow-sm mx-auto">
            🗺️
          </div>
          <div className="w-12 h-12 border-4 border-[#58cc02] border-t-transparent rounded-full animate-spin mx-auto" />
          <h2 className="text-xl font-black text-slate-800">
            {initializing ? 'CALA is synthesizing your curriculum...' : 'Loading personalized roadmap...'}
          </h2>
          <p className="text-xs text-slate-500 font-bold">
            Constructing adaptive levels tailored to your mind profile.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 bg-[#f8fafc]">
        <div className="bg-white border-2 border-rose-200 border-b-4 border-rose-300 rounded-3xl p-8 max-w-md text-center shadow-sm">
          <div className="text-4xl mb-3">⚠️</div>
          <h3 className="text-lg font-black text-slate-900 mb-2">Roadmap Load Error</h3>
          <p className="text-rose-600 text-xs font-bold mb-6">{error}</p>
          <button onClick={onBack} className="btn-duo-secondary w-full py-3 text-xs cursor-pointer">
            ← RETURN TO DASHBOARD
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen px-4 py-8 max-w-3xl mx-auto">
      {/* Top Bar */}
      <div className="flex items-center justify-between mb-8">
        <button
          onClick={onBack}
          className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer"
        >
          ← HOME
        </button>
        <span className="pill-stat pill-green text-xs">
          Stage: {currentStage || 'IN_PROGRESS'}
        </span>
      </div>

      {/* Hero Header & Progress */}
      <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[#15803d] text-xs font-black uppercase mb-3">
          PERSONALIZED ADAPTIVE ROADMAP
        </div>
        <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight mb-2">
          {topic}
        </h1>
        <p className="text-slate-500 text-sm font-medium mb-6">
          {completedCount} of {levels.length} levels completed • {progressPercent}% mastered
        </p>

        {/* Progress Bar */}
        <div className="h-4 w-full rounded-full bg-slate-100 border border-slate-200 overflow-hidden p-0.5 max-w-lg mx-auto">
          <div
            className="h-full rounded-full bg-[#58cc02] transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Gamified Roadmap Path */}
      <div className="relative pb-16">
        {/* Central Winding Line */}
        <div className="absolute left-8 sm:left-1/2 top-4 bottom-4 w-1.5 bg-emerald-200 -translate-x-1/2 rounded-full -z-0" />

        <div className="space-y-8 relative z-10">
          {levels.map((level, idx) => {
            const isCompleted = level.status === 'COMPLETED';
            const isUnlocked = level.status === 'UNLOCKED' || level.status === 'IN_PROGRESS';
            const isLocked = level.status === 'LOCKED';

            return (
              <div
                key={level.level_id}
                className={`flex flex-col sm:flex-row items-center gap-6 ${
                  idx % 2 === 1 ? 'sm:flex-row-reverse' : ''
                }`}
              >
                {/* Visual Level Node (Duolingo Style 3D Circle) */}
                <div className="sm:w-1/2 flex justify-start sm:justify-end sm:pr-8">
                  <div
                    onClick={() => isUnlocked && onEnterLevel(level.level_id, sessionId, level)}
                    className={`w-20 h-20 rounded-full flex flex-col items-center justify-center transition-all cursor-pointer select-none shadow-md ${
                      isCompleted
                        ? 'bg-[#ffc800] border-b-6 border-[#e5a500] text-white hover:scale-105 active:scale-95'
                        : isUnlocked
                        ? 'bg-[#58cc02] border-b-6 border-[#46a302] text-white ring-6 ring-emerald-100 hover:scale-105 active:scale-95'
                        : 'bg-slate-200 border-b-6 border-slate-300 text-slate-400 cursor-not-allowed'
                    }`}
                    title={isLocked ? 'Locked • Complete previous levels' : `Enter Level ${level.level_number}`}
                  >
                    <span className="text-2xl leading-none">
                      {isCompleted ? '⭐' : isUnlocked ? '🚀' : '🔒'}
                    </span>
                    <span className="text-[11px] font-black mt-1">
                      LVL {level.level_number}
                    </span>
                  </div>
                </div>

                {/* Level Card Description */}
                <div className="w-full sm:w-1/2">
                  <div
                    onClick={() => isUnlocked && onEnterLevel(level.level_id, sessionId, level)}
                    className={`card-duo p-6 transition-all ${
                      isUnlocked
                        ? 'border-emerald-300 border-b-emerald-500 shadow-md cursor-pointer hover:-translate-y-1'
                        : isCompleted
                        ? 'border-amber-200 opacity-90'
                        : 'border-slate-200 opacity-60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className={`text-[11px] font-black uppercase tracking-wider ${
                        isCompleted ? 'text-amber-600' : isUnlocked ? 'text-[#15803d]' : 'text-slate-400'
                      }`}>
                        Level {level.level_number} • {level.status}
                      </span>
                      <span className={`text-[11px] font-black px-2.5 py-0.5 rounded-full ${
                        level.difficulty === 'Easy' || level.difficulty === 'Beginner'
                          ? 'bg-emerald-100 text-emerald-800'
                          : level.difficulty === 'Medium'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}>
                        {level.difficulty}
                      </span>
                    </div>

                    <h3 className="text-lg font-black text-slate-900 mb-1">
                      {level.title}
                    </h3>
                    <p className="text-xs text-slate-500 font-medium leading-relaxed">
                      {level.objective || 'Master key conceptual foundations and practical applications.'}
                    </p>

                    {isUnlocked && (
                      <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                        <span className="text-xs font-black text-[#58cc02]">
                          Ready to Learn • 6 Agents Active
                        </span>
                        <button className="btn-duo-green px-4 py-1.5 text-[11px] tracking-wider cursor-pointer">
                          START →
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default RoadmapView;
