import React, { useEffect, useState } from 'react';
import { OrchestrationAPI } from '../../api/clarioApi';
import type { FinalReportData } from '../../api/clarioApi';

interface FinalReportViewProps {
  sessionId: string;
  onBackToRoadmap: () => void;
  onStartNewSession: () => void;
}

export const FinalReportView: React.FC<FinalReportViewProps> = ({
  sessionId,
  onBackToRoadmap,
  onStartNewSession,
}) => {
  const [report, setReport] = useState<FinalReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const data = await OrchestrationAPI.getFinalReport(sessionId);
        setReport(data);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || 'Failed to load final report.');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [sessionId]);

  const handlePrint = () => {
    window.print();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-[#f8fafc]">
        <div className="text-center space-y-4">
          <div className="w-12 h-12 border-4 border-[#58cc02] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-slate-500 font-bold text-sm">Synthesizing your official CLARIO Final Learning Report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-[#f8fafc]">
        <div className="card-duo max-w-md w-full text-center space-y-4 p-8">
          <div className="text-4xl">⚠️</div>
          <h2 className="text-xl font-black text-slate-900">Unable to load report</h2>
          <p className="text-xs text-slate-500 font-bold">{error || 'Final report is not yet generated.'}</p>
          <button
            onClick={onBackToRoadmap}
            className="btn-duo-secondary w-full py-3 text-xs cursor-pointer"
          >
            ← Back to Roadmap
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-10 px-4 max-w-4xl mx-auto space-y-8 bg-[#f8fafc] print:bg-white print:p-0">
      {/* Top action bar (hidden on print) */}
      <div className="flex items-center justify-between print:hidden">
        <button
          onClick={onBackToRoadmap}
          className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer"
        >
          ← ROADMAP
        </button>
        <div className="flex items-center gap-3">
          <button
            onClick={handlePrint}
            className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer flex items-center gap-1.5"
          >
            <span>🖨️</span>
            <span>Print / PDF</span>
          </button>
          <button
            onClick={onStartNewSession}
            className="btn-duo-green px-5 py-2 text-xs font-black tracking-wider cursor-pointer"
          >
            + START NEW GOAL 🚀
          </button>
        </div>
      </div>

      {/* Main Report Container */}
      <div className="bg-white rounded-3xl border-2 border-emerald-200 border-b-6 border-emerald-400 p-8 sm:p-12 shadow-sm space-y-10 print:border-none print:p-4 print:shadow-none">
        {/* Certificate / Official Header */}
        <div className="border-b-2 border-slate-100 pb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[#15803d] text-xs font-black uppercase tracking-wider mb-3">
              Official CLARIO Mastery Certificate
            </div>
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900">
              {report.topic}
            </h1>
            <p className="text-slate-500 text-xs font-bold mt-1">
              Completed on {new Date(report.created_at).toLocaleDateString()} • Session {report.session_id.slice(0, 12)}
            </p>
          </div>
          <div className="w-20 h-20 rounded-3xl bg-[#ffc800] border-b-6 border-[#e5a500] text-white flex items-center justify-center text-4xl shadow-md shrink-0">
            👑
          </div>
        </div>

        {/* Executive Summary */}
        <div className="bg-[#f0fdf4] border-2 border-emerald-200 rounded-2xl p-6">
          <h2 className="text-xs uppercase tracking-widest text-[#15803d] font-black mb-2">Executive Summary</h2>
          <p className="text-slate-800 text-sm md:text-base leading-relaxed font-medium">
            {report.executive_summary}
          </p>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
          <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 text-center">
            <span className="text-[11px] font-black uppercase text-slate-500">Completed Levels</span>
            <p className="text-2xl font-black text-[#15803d] mt-1">{report.completed_levels} / {report.total_levels}</p>
          </div>
          <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 text-center">
            <span className="text-[11px] font-black uppercase text-slate-500">Total Experience</span>
            <p className="text-2xl font-black text-[#a16207] mt-1">{report.total_xp} XP</p>
          </div>
          <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 text-center">
            <span className="text-[11px] font-black uppercase text-slate-500">Mastered Concepts</span>
            <p className="text-2xl font-black text-[#6d28d9] mt-1">{report.mastered_concepts.length}</p>
          </div>
          <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 text-center">
            <span className="text-[11px] font-black uppercase text-slate-500">Remediations Overcome</span>
            <p className="text-2xl font-black text-[#c2410c] mt-1">{report.remediations_count}</p>
          </div>
        </div>

        {/* Mastered Concepts Breakdown */}
        <div className="space-y-4">
          <h3 className="text-base font-black uppercase tracking-wider text-slate-900">Concept Performance Mastery</h3>
          <div className="grid gap-3">
            {report.mastered_concepts.map((c) => (
              <div
                key={c.concept}
                className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-200"
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-extrabold text-sm text-slate-900">{c.concept}</h4>
                  <span className="font-mono text-xs font-black text-[#15803d] bg-emerald-100 px-2.5 py-0.5 rounded-full border border-emerald-200">
                    {Math.round(c.mastery_score * 100)}% Mastery
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-600 mt-2 font-medium">
                  <div>
                    <span className="font-bold text-slate-400">Understanding:</span> {c.understanding}
                  </div>
                  <div>
                    <span className="font-bold text-slate-400">Reasoning:</span> {c.reasoning}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Strengths & Growth Areas */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="p-5 rounded-2xl bg-[#f0fdf4] border-2 border-emerald-200">
            <h4 className="text-xs font-black uppercase tracking-wider text-[#15803d] mb-3 flex items-center gap-2">
              <span>🌟</span> Core Strengths Demonstrated
            </h4>
            <ul className="space-y-2 text-xs text-slate-700 font-medium">
              {report.strengths.map((s, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-[#58cc02] font-black shrink-0">✓</span>
                  <span>{s}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="p-5 rounded-2xl bg-[#f8fafc] border-2 border-slate-200">
            <h4 className="text-xs font-black uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-2">
              <span>🚀</span> Growth & Retention Next Steps
            </h4>
            <ul className="space-y-2 text-xs text-slate-700 font-medium">
              {report.growth_areas.map((g, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-[#1cb0f6] font-black shrink-0">→</span>
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Verification Footer */}
        <div className="border-t-2 border-slate-100 pt-6 text-center text-xs text-slate-400 font-bold">
          Validated by CLARIO-AI Autonomous Learning Engine • Multi-Agent Pipeline Verification
        </div>
      </div>
    </div>
  );
};
