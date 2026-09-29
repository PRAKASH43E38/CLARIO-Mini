import React, { useEffect, useState } from 'react';
import { RewardsAPI } from '../api/clarioApi';
import type { RewardSummary, BadgeItem } from '../api/clarioApi';

export const RewardsWidget: React.FC = () => {
  const [rewards, setRewards] = useState<RewardSummary | null>(null);
  const [badgeCatalog, setBadgeCatalog] = useState<BadgeItem[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'badges' | 'history'>('badges');

  const fetchRewards = async () => {
    try {
      const data = await RewardsAPI.getRewards();
      setRewards(data);
    } catch {
      // Ignore if unauthenticated
    }
  };

  const openModal = async () => {
    setShowModal(true);
    try {
      const bData = await RewardsAPI.getBadges();
      setBadgeCatalog(bData.badges);
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    fetchRewards();
    const interval = setInterval(fetchRewards, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!rewards) return null;

  return (
    <>
      <div className="flex items-center gap-2.5">
        {/* Streak Pill */}
        <button
          onClick={openModal}
          className="pill-stat pill-streak cursor-pointer hover:scale-105 active:scale-95 transition"
          title={`${rewards.streak.current_streak} Day Learning Streak`}
        >
          <span className="text-base leading-none">🔥</span>
          <span>{rewards.streak.current_streak}d</span>
        </button>

        {/* XP & Level Pill */}
        <button
          onClick={openModal}
          className="pill-stat pill-xp cursor-pointer hover:scale-105 active:scale-95 transition"
          title={`${rewards.total_xp} Total XP (Level ${rewards.level})`}
        >
          <span className="text-base leading-none">⚡</span>
          <span>Lv.{rewards.level}</span>
          <span className="text-amber-400">•</span>
          <span>{rewards.total_xp} XP</span>
        </button>

        {/* Badges Pill */}
        <button
          onClick={openModal}
          className="pill-stat pill-badge cursor-pointer hover:scale-105 active:scale-95 transition"
          title={`${rewards.badge_count} Badges Earned`}
        >
          <span className="text-base leading-none">🏅</span>
          <span>{rewards.badge_count}</span>
        </button>
      </div>

      {/* Rewards Detailed Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
          <div className="bg-white border-2 border-slate-200 border-b-4 border-slate-300 rounded-3xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="p-6 border-b-2 border-slate-100 flex items-center justify-between bg-[#f8fafc]">
              <div className="flex items-center gap-3.5">
                <div className="w-12 h-12 rounded-2xl bg-[#58cc02] border-b-4 border-[#46a302] flex items-center justify-center text-2xl shadow-sm text-white">
                  🏆
                </div>
                <div>
                  <h3 className="text-xl font-black text-slate-900">CLARIO Achievements & XP</h3>
                  <p className="text-xs text-slate-500 font-bold">Real learning progress earned across all 6 agents</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-700 p-2 rounded-xl hover:bg-slate-100 transition cursor-pointer font-bold text-lg"
              >
                ✕
              </button>
            </div>

            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-3 gap-3 p-6 bg-white border-b-2 border-slate-100">
              <div className="bg-[#f0fdf4] rounded-2xl p-4 text-center border-2 border-emerald-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Experience</span>
                <p className="text-2xl font-black text-[#15803d] mt-1">{rewards.total_xp} XP</p>
              </div>
              <div className="bg-[#fff7ed] rounded-2xl p-4 text-center border-2 border-orange-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Current Streak</span>
                <p className="text-2xl font-black text-[#c2410c] mt-1">🔥 {rewards.streak.current_streak} Days</p>
              </div>
              <div className="bg-[#faf5ff] rounded-2xl p-4 text-center border-2 border-purple-100">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Badges Unlocked</span>
                <p className="text-2xl font-black text-[#6d28d9] mt-1">{rewards.badge_count} Earned</p>
              </div>
            </div>

            {/* Tabs */}
            <div className="flex border-b-2 border-slate-100 px-6 gap-6 bg-white">
              <button
                onClick={() => setActiveTab('badges')}
                className={`pb-3 pt-2 text-sm font-bold transition border-b-4 cursor-pointer ${
                  activeTab === 'badges'
                    ? 'border-[#58cc02] text-[#15803d]'
                    : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                🏅 Badges & Mastery
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`pb-3 pt-2 text-sm font-bold transition border-b-4 cursor-pointer ${
                  activeTab === 'history'
                    ? 'border-[#58cc02] text-[#15803d]'
                    : 'border-transparent text-slate-400 hover:text-slate-600'
                }`}
              >
                📜 XP History
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto flex-1 space-y-4 bg-[#f8fafc]">
              {activeTab === 'badges' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {badgeCatalog.map((b) => (
                    <div
                      key={b.badge_key}
                      className={`p-4 rounded-2xl border-2 transition-all flex items-start gap-3.5 ${
                        b.earned
                          ? 'bg-white border-emerald-200 border-b-4 border-b-emerald-400 shadow-sm'
                          : 'bg-white/60 border-slate-200 opacity-50'
                      }`}
                    >
                      <div className="text-3xl p-2.5 rounded-2xl bg-[#f8fafc] border border-slate-200 shrink-0">
                        {b.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <h4 className="font-extrabold text-sm text-slate-800 truncate">{b.badge_name}</h4>
                          {b.earned && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-extrabold shrink-0 border border-emerald-200">
                              Unlocked
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 font-medium mt-1 line-clamp-2">{b.description}</p>
                        {b.awarded_at && (
                          <p className="text-[10px] text-emerald-600 font-bold mt-1.5">
                            ✓ Earned {new Date(b.awarded_at).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2.5">
                  {rewards.recent_xp.length === 0 ? (
                    <div className="text-center py-10">
                      <span className="text-4xl">🌱</span>
                      <p className="text-slate-500 font-bold text-sm mt-2">No XP earned yet.</p>
                      <p className="text-xs text-slate-400 mt-1">Start your first learning level to earn rewards!</p>
                    </div>
                  ) : (
                    rewards.recent_xp.map((tx) => (
                      <div
                        key={tx.transaction_id}
                        className="flex items-center justify-between p-3.5 rounded-2xl bg-white border-2 border-slate-200/80 hover:border-emerald-200 transition shadow-sm"
                      >
                        <div>
                          <p className="font-bold text-sm text-slate-800">{tx.reason}</p>
                          <p className="text-[11px] text-slate-400 font-medium mt-0.5">
                            {new Date(tx.created_at).toLocaleString()}
                          </p>
                        </div>
                        <span className="px-3 py-1 rounded-xl bg-emerald-100 border border-emerald-200 text-[#15803d] font-mono font-black text-xs shadow-xs">
                          +{tx.xp_amount} XP
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
