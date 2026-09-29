import React, { useEffect, useState } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const QUESTIONS = [
  'When you learn something new, what usually keeps you going?',
  'What makes you lose interest while learning?',
  'If you get stuck, what would you prefer CLARIO to do?',
  'Which kind of learning experience feels most natural to you?',
  'What would make you want to come back and continue learning?',
];

function responseError(payload: unknown, fallback: string): string {
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

export const MindQuestions: React.FC<{
  user: { user_id: string; email: string };
  editing: boolean;
  onComplete: () => void;
}> = ({ user, editing, onComplete }) => {
  const [answers, setAnswers] = useState<string[]>(Array(QUESTIONS.length).fill(''));
  const [current, setCurrent] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    let active = true;
    fetch(`${API}/mind-profile/${encodeURIComponent(user.user_id)}`, {
      credentials: 'include',
    })
      .then(async (response) => {
        const data: unknown = await response.json();
        if (!response.ok) {
          throw new Error(responseError(data, 'Could not load your learning profile.'));
        }
        if (
          typeof data !== 'object'
          || data === null
          || !('answers' in data)
          || !Array.isArray(data.answers)
          || !data.answers.every((answer) => typeof answer === 'string')
        ) {
          throw new Error('The server returned invalid learning profile information.');
        }
        return { answers: data.answers };
      })
      .then((data) => {
        if (!active || !Array.isArray(data.answers)) return;
        const savedAnswers = Array(QUESTIONS.length).fill('');
        data.answers.slice(0, QUESTIONS.length).forEach((answer, index) => {
          savedAnswers[index] = answer;
        });
        setAnswers(savedAnswers);
        if (!editing) {
          const nextQuestion = savedAnswers.findIndex((answer: string) => !answer.trim());
          setCurrent(nextQuestion === -1 ? 0 : nextQuestion);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Could not load your learning profile.');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [editing, user.user_id]);

  const saveAnswers = async (finalAnswers: string[]) => {
    setSaving(true);
    setError(null);
    try {
      const response = await fetch(`${API}/mind-profile/${encodeURIComponent(user.user_id)}`, {
        method: editing ? 'PUT' : 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: finalAnswers }),
      });
      const data: unknown = await response.json();
      if (!response.ok) {
        throw new Error(responseError(data, 'Could not save your learning profile.'));
      }
      setComplete(true);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not save your learning profile.');
    } finally {
      setSaving(false);
    }
  };

  const next = () => {
    const answer = answers[current].trim();
    if (!answer) {
      setError('Please share a little about yourself before moving on.');
      return;
    }

    const updatedAnswers = [...answers];
    updatedAnswers[current] = answer;
    setAnswers(updatedAnswers);
    setError(null);

    if (current === QUESTIONS.length - 1) {
      void saveAnswers(updatedAnswers);
    } else {
      setCurrent((index) => index + 1);
    }
  };

  if (complete) {
    return (
      <div className="min-h-screen bg-[#f8fafc] flex flex-col justify-center items-center p-6">
        <div className="w-full max-w-xl text-center">
          <div className="w-20 h-20 rounded-3xl bg-[#58cc02] border-b-6 border-[#46a302] flex items-center justify-center text-4xl text-white shadow-lg mx-auto mb-6">
            🎉
          </div>
          <div className="card-duo-green p-8 text-center bg-white">
            <h1 className="text-3xl font-black text-slate-900 mb-2">
              Your Mind Profile is Ready!
            </h1>
            <p className="text-slate-600 font-medium mb-8 max-w-md mx-auto">
              CLARIO and your 6 learning agents now understand how you learn best. These cognitive signals will adaptively personalize every single roadmap level.
            </p>
            <button
              onClick={onComplete}
              className="btn-duo-green px-8 py-4 text-base tracking-wider cursor-pointer"
            >
              CONTINUE TO LEARNING ENGINE →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] flex flex-col justify-center items-center p-6">
      <div className="w-full max-w-2xl">
        {/* Step Indicator Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 rounded-xl bg-emerald-100 text-[#15803d] font-black text-sm flex items-center justify-center">
              🧠
            </span>
            <span className="text-xs font-black uppercase tracking-wider text-slate-500">
              {editing ? 'Editing Preferences' : 'Mind Profile • 5 Questions'}
            </span>
          </div>
          <span className="text-xs font-extrabold text-[#15803d] bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
            {current + 1} of {QUESTIONS.length}
          </span>
        </div>

        {/* Thick Duolingo Progress Bar */}
        <div
          className="mb-8 h-4 w-full rounded-full bg-slate-200 border border-slate-300/60 overflow-hidden p-0.5"
          role="progressbar"
          aria-label="Question progress"
          aria-valuemin={1}
          aria-valuemax={QUESTIONS.length}
          aria-valuenow={current + 1}
        >
          <div
            className="h-full rounded-full bg-[#58cc02] transition-all duration-300"
            style={{ width: `${((current + 1) / QUESTIONS.length) * 100}%` }}
          />
        </div>

        {/* Question Card */}
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm">
          <div className="mb-6">
            <span className="text-xs font-black text-[#58cc02] uppercase tracking-wider">Question {current + 1}</span>
            <h2 className="text-2xl font-black text-slate-900 mt-1 leading-snug">
              {QUESTIONS[current]}
            </h2>
          </div>

          <div className="mb-6">
            <textarea
              id="mind-answer"
              value={answers[current]}
              onChange={(event) => {
                const updated = [...answers];
                updated[current] = event.target.value;
                setAnswers(updated);
              }}
              rows={4}
              maxLength={2000}
              className="w-full rounded-2xl border-2 border-slate-200 px-4 py-3.5 text-slate-800 placeholder-slate-400 font-medium focus:outline-none focus:border-[#58cc02] focus:bg-emerald-50/20 transition resize-vertical text-base"
              placeholder="Type your honest thoughts here..."
              autoFocus
            />
          </div>

          {error && (
            <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-3 mb-5 text-xs text-rose-700 font-bold flex items-center gap-2">
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <p className="text-xs text-slate-400 font-bold mb-4">Loading saved preferences...</p>
          )}

          <div className="flex items-center justify-between gap-4 pt-2">
            <button
              type="button"
              onClick={() => {
                setCurrent((index) => Math.max(0, index - 1));
                setError(null);
              }}
              className="btn-duo-secondary px-6 py-3.5 text-xs cursor-pointer"
              disabled={current === 0 || loading || saving}
            >
              ← BACK
            </button>
            <button
              type="button"
              onClick={next}
              disabled={loading || saving}
              className="btn-duo-green px-8 py-3.5 text-xs cursor-pointer"
            >
              {saving
                ? 'SAVING...'
                : current < QUESTIONS.length - 1
                  ? 'CONTINUE →'
                  : editing
                    ? 'SAVE PREFERENCES'
                    : 'FINISH PROFILE ✓'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
