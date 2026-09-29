import React, { useEffect, useState } from 'react';
import { SessionAPI } from '../../api/sessionApi';

interface ReviewScreenProps {
    sessionId: string;
    onEdit?: () => void;
    onComplete?: () => void;
}

const ReviewScreen: React.FC<ReviewScreenProps> = ({ sessionId, onEdit, onComplete }) => {
    const [inputs, setInputs] = useState<any>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (sessionId) {
            fetchInputs();
        }
    }, [sessionId]);

    const fetchInputs = async () => {
        try {
            const data = await SessionAPI.getSessionInputs(sessionId);
            setInputs(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load inputs.');
        } finally {
            setLoading(false);
        }
    };

    const handleStartLearning = async () => {
        setSaving(true);
        setError(null);
        try {
            await SessionAPI.finalizeSession(sessionId);
            if (onComplete) {
                onComplete();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to finalize session.');
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return (
            <div className="max-w-2xl mx-auto py-16 px-4 text-center">
                <div className="w-12 h-12 border-4 border-[#58cc02] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-sm font-bold text-slate-500">Loading session summary...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-2xl mx-auto py-16 px-4 text-center">
                <div className="bg-rose-50 border-2 border-rose-200 rounded-3xl p-6 text-rose-700">
                    <p className="font-bold text-sm">{error}</p>
                    <button
                        onClick={onEdit}
                        className="btn-duo-secondary mt-4 px-6 py-2 text-xs cursor-pointer"
                    >
                        ← Return to inputs
                    </button>
                </div>
            </div>
        );
    }

    if (!inputs) {
        return (
            <div className="max-w-2xl mx-auto py-16 px-4 text-center">
                <p className="text-sm font-bold text-slate-500">No session inputs found.</p>
            </div>
        );
    }

    return (
        <div className="max-w-2xl mx-auto py-8 px-4">
            <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
                <div className="text-center mb-6">
                    <div className="w-14 h-14 rounded-2xl bg-[#58cc02] border-b-4 border-[#46a302] text-white text-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
                        📋
                    </div>
                    <span className="text-xs font-black uppercase tracking-wider text-[#15803d]">CALA Curriculum Synthesis</span>
                    <h1 className="text-2xl md:text-3xl font-black text-slate-900 mt-1">Review Your Learning Journey</h1>
                    <p className="text-xs md:text-sm text-slate-500 font-medium mt-1">
                        Confirm your focus before CALA generates your personalized multi-level roadmap.
                    </p>
                </div>

                <div className="space-y-3.5 mb-8">
                    <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-100 flex items-start gap-3.5">
                        <span className="text-2xl p-1 bg-white rounded-xl border border-slate-200 shrink-0">🎯</span>
                        <div>
                            <span className="text-[11px] font-black uppercase tracking-wider text-slate-500">Target Task</span>
                            <p className="text-base font-bold text-slate-900 mt-0.5">{inputs.task}</p>
                        </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-100 flex items-start gap-3.5">
                        <span className="text-2xl p-1 bg-white rounded-xl border border-slate-200 shrink-0">🏆</span>
                        <div>
                            <span className="text-[11px] font-black uppercase tracking-wider text-slate-500">Measurable Goal</span>
                            <p className="text-base font-bold text-slate-900 mt-0.5">{inputs.goal}</p>
                        </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-100 flex items-start gap-3.5">
                        <span className="text-2xl p-1 bg-white rounded-xl border border-slate-200 shrink-0">🌱</span>
                        <div>
                            <span className="text-[11px] font-black uppercase tracking-wider text-slate-500">Learner Baseline</span>
                            <p className="text-base font-bold text-slate-900 mt-0.5">{inputs.learner_state}</p>
                        </div>
                    </div>

                    <div className="p-4 rounded-2xl bg-[#f8fafc] border-2 border-slate-100 flex items-start gap-3.5">
                        <span className="text-2xl p-1 bg-white rounded-xl border border-slate-200 shrink-0">✨</span>
                        <div>
                            <span className="text-[11px] font-black uppercase tracking-wider text-slate-500">Familiar Interest / Analogy</span>
                            <p className="text-base font-bold text-slate-900 mt-0.5">{inputs.interest}</p>
                        </div>
                    </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3.5">
                    <button
                        onClick={onEdit}
                        className="btn-duo-secondary flex-1 py-3.5 text-xs tracking-wider cursor-pointer"
                    >
                        ← EDIT INPUTS
                    </button>
                    <button
                        onClick={handleStartLearning}
                        disabled={saving}
                        className="btn-duo-green flex-2 py-3.5 text-xs tracking-wider cursor-pointer"
                    >
                        {saving ? 'SYNTHESIZING WITH CALA...' : 'GENERATE ROADMAP WITH CALA 🚀'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ReviewScreen;
