import React, { useState } from 'react';
import { SessionAPI } from '../../api/sessionApi';

interface InputFormProps {
    sessionId: string;
    onBack?: () => void;
    onComplete?: () => void;
}

const InputForm: React.FC<InputFormProps> = ({ sessionId, onBack, onComplete }) => {
    const [inputs, setInputs] = useState({
        task: '',
        goal: '',
        learner_state: '',
        interest: '',
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
        setInputs({ ...inputs, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            await SessionAPI.saveInputs(sessionId, inputs);
            if (onComplete) {
                onComplete();
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save inputs. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto py-8 px-4">
            <div className="flex items-center justify-between mb-6">
                <button
                    onClick={onBack}
                    className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer"
                >
                    ← BACK
                </button>
                <div className="flex items-center gap-2">
                    <span className="text-xs font-black text-slate-500 uppercase tracking-wider">
                        Session Setup • 4 Inputs
                    </span>
                    <span className="w-2.5 h-2.5 rounded-full bg-[#58cc02]" />
                </div>
            </div>

            <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
                <div className="mb-6">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[#15803d] text-xs font-extrabold uppercase mb-2">
                        Target Concept Definition
                    </div>
                    <h1 className="text-2xl md:text-3xl font-black text-slate-900">Define Your Learning Journey</h1>
                    <p className="text-xs md:text-sm text-slate-500 font-medium mt-1">
                        CALA uses these four exact signals to synthesize your personalized curriculum.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                    <div>
                        <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                            1. Target Task <span className="text-slate-400 font-bold lowercase">(&ldquo;what do you want to learn or build?&rdquo;)</span>
                        </label>
                        <textarea
                            name="task"
                            value={inputs.task}
                            onChange={handleChange}
                            required
                            className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition resize-none"
                            placeholder="e.g. Master React 19 Server Actions, NEET Biology Genetics, GATE OS Scheduling..."
                            rows={2}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                            2. Measurable Goal <span className="text-slate-400 font-bold lowercase">(&ldquo;what is your concrete target milestone?&rdquo;)</span>
                        </label>
                        <textarea
                            name="goal"
                            value={inputs.goal}
                            onChange={handleChange}
                            required
                            className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition resize-none"
                            placeholder="e.g. Build an end-to-end fullstack app, pass technical interview, score top percentile..."
                            rows={2}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                            3. Current Learner State <span className="text-slate-400 font-bold lowercase">(&ldquo;what do you already know?&rdquo;)</span>
                        </label>
                        <textarea
                            name="learner_state"
                            value={inputs.learner_state}
                            onChange={handleChange}
                            required
                            className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition resize-none"
                            placeholder="e.g. Total beginner with zero background, or comfortable with JavaScript basics..."
                            rows={2}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-black uppercase tracking-wider text-slate-700 mb-1.5">
                            4. Familiar Interest Context <span className="text-slate-400 font-bold lowercase">(&ldquo;what real-world analogies do you love?&rdquo;)</span>
                        </label>
                        <textarea
                            name="interest"
                            value={inputs.interest}
                            onChange={handleChange}
                            required
                            className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition resize-none"
                            placeholder="e.g. Gaming, Football, Marvel movies, Space exploration, Finance..."
                            rows={2}
                        />
                    </div>

                    {error && (
                        <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-3 text-xs text-rose-700 font-bold flex items-center gap-2">
                            <span>⚠️</span>
                            <span>{error}</span>
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer mt-4"
                    >
                        {loading ? 'PROCESSING INPUTS...' : 'CONTINUE TO REVIEW & CALA →'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default InputForm;
