import React, { useState, useEffect } from 'react';
import { OrchestrationAPI } from '../../api/clarioApi';
import { AGENT_CHARACTERS } from '../../config/agentCharacters';

interface LevelInfo {
  level_id: string;
  title: string;
  objective: string;
  difficulty: string;
  level_number?: number;
  status?: string;
}

interface LevelExecutionProps {
  sessionId: string;
  levelId: string;
  level: LevelInfo;
  onBack: () => void;
  onLevelCompleted: () => void;
  onGoalCompleted: () => void;
}

interface AgentStateInfo {
  name: string;
  role: string;
  status: 'LOCKED' | 'READY' | 'RUNNING' | 'WAITING_FOR_USER' | 'COMPLETED' | 'REMEDIATING' | 'FAILED';
}

interface WorkflowStateData {
  session_id: string;
  level_id: string;
  level_title: string;
  level_objective: string;
  agents: {
    clario_ai: AgentStateInfo;
    nova: AgentStateInfo;
    mira: AgentStateInfo;
    ayan: AgentStateInfo;
    kira: AgentStateInfo;
    zayn: AgentStateInfo;
    elara: AgentStateInfo;
  };
  counts: {
    thinking_responses: number;
    application_responses: number;
    quiz_responses: number;
  };
  latest_decision?: any;
}

const statusBadgeStyles: Record<string, { bg: string; text: string; border: string; icon: string }> = {
  COMPLETED: { bg: 'bg-[#dcfce7]', text: 'text-[#15803d]', border: 'border-[#86efac]', icon: '✓' },
  WAITING_FOR_USER: { bg: 'bg-[#fef9c3]', text: 'text-[#a16207]', border: 'border-[#fde047]', icon: '●' },
  RUNNING: { bg: 'bg-[#e0f2fe]', text: 'text-[#0369a1]', border: 'border-[#7dd3fc]', icon: '⚡' },
  REMEDIATING: { bg: 'bg-[#ffedd5]', text: 'text-[#c2410c]', border: 'border-[#fdba74]', icon: '🔄' },
  READY: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: '○' },
  LOCKED: { bg: 'bg-slate-100', text: 'text-slate-400', border: 'border-slate-200', icon: '🔒' },
  FAILED: { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', icon: '✕' },
};

export const LevelExecution: React.FC<LevelExecutionProps> = ({
  sessionId,
  levelId,
  level,
  onBack,
  onLevelCompleted,
  onGoalCompleted,
}) => {
  // Live workflow state
  const [workflowState, setWorkflowState] = useState<WorkflowStateData | null>(null);
  const [activeStep, setActiveStep] = useState<'nova' | 'mira' | 'ayan' | 'kira' | 'zayn' | 'decision'>('mira');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Step payloads
  const [novaResearch, setNovaResearch] = useState<{ summary: string; sources: any[]; facts: string[] }>({
    summary: '',
    sources: [],
    facts: [],
  });
  const [miraLesson, setMiraLesson] = useState<string>('');
  const [miraInterviewUrl, setMiraInterviewUrl] = useState<string | null>(null);
  const [miraResponseText, setMiraResponseText] = useState<string>('I have read and understood the foundational concepts.');
  const [miraNeedsClarification, setMiraNeedsClarification] = useState(false);

  // Ayan challenges
  const [ayanData, setAyanData] = useState<{ challenge_id: string; questions: any[] }>({ challenge_id: '', questions: [] });
  const [ayanAnswers, setAyanAnswers] = useState<Record<string, string>>({});

  // Kira scenarios
  const [kiraData, setKiraData] = useState<{ scenario_id: string; scenarios: any[] }>({ scenario_id: '', scenarios: [] });
  const [kiraResponses, setKiraResponses] = useState<Record<string, string>>({});

  // Zayn quiz (10 questions)
  const [zaynData, setZaynData] = useState<{ quiz_id: string; questions: any[] }>({ quiz_id: '', questions: [] });
  const [quizAnswers, setQuizAnswers] = useState<Record<string, string>>({});
  const [quizTimer, setQuizTimer] = useState<number>(30);
  const [currentQuizIdx, setCurrentQuizIdx] = useState<number>(0);

  // Decision & Evaluation
  const [decisionData, setDecisionData] = useState<any>(null);

  // Load and start interactive level
  useEffect(() => {
    startLevel();
  }, [levelId, sessionId]);

  // Quiz countdown timer (static intervals, no motion effects)
  useEffect(() => {
    if (activeStep !== 'zayn' || !zaynData.questions.length) return;
    const interval = setInterval(() => {
      setQuizTimer((t) => (t > 0 ? t - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [activeStep, currentQuizIdx, zaynData.questions.length]);

  const refreshWorkflowState = async () => {
    try {
      const state = await OrchestrationAPI.getStepState(levelId, sessionId);
      setWorkflowState(state);
    } catch {
      // Fallback
    }
  };

  const startLevel = async () => {
    setLoading(true);
    setError(null);
    try {
      // Step 1: Start interactive level (Nova research + Mira lesson)
      const data = await OrchestrationAPI.startStep(levelId, sessionId);
      setNovaResearch(data.nova || { summary: '', sources: [], facts: [] });
      setMiraLesson(data.mira?.lesson_content || '');
      setMiraInterviewUrl(data.mira?.interview_url || (data.mira?.is_interview ? 'https://www.indiabix.com/' : null));
      setActiveStep('mira');
      await refreshWorkflowState();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to start learning level.');
    } finally {
      setLoading(false);
    }
  };

  // Submit Mira and receive Ayan
  const handleMiraSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await OrchestrationAPI.submitMiraComplete(levelId, sessionId, miraResponseText);
      setAyanData(data.ayan || { challenge_id: '', questions: [] });
      setActiveStep('ayan');
      await refreshWorkflowState();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit teaching response.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Ayan and receive Kira
  const handleAyanSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await OrchestrationAPI.submitAyanThinking(levelId, sessionId, ayanData.challenge_id, ayanAnswers);
      setKiraData(data.kira || { scenario_id: '', scenarios: [] });
      setActiveStep('kira');
      await refreshWorkflowState();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit critical thinking answers.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Kira and receive Zayn 10-question quiz
  const handleKiraSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await OrchestrationAPI.submitKiraApplication(levelId, sessionId, kiraData.scenario_id, kiraResponses);
      const questions = data.zayn?.questions || [];
      setZaynData({ quiz_id: data.zayn?.quiz_id, questions });
      setActiveStep('zayn');
      setCurrentQuizIdx(0);
      if (questions.length > 0) {
        setQuizTimer(questions[0].time_limit_seconds || 30);
      }
      await refreshWorkflowState();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit real-world application.');
    } finally {
      setSubmitting(false);
    }
  };

  // Submit Zayn quiz and receive Elara + CLARIO-AI decision
  const handleZaynSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const formattedAnswers = zaynData.questions.map((q) => ({
        question_id: q.question_id,
        answer: quizAnswers[q.question_id] || 'No answer submitted',
        response_time_seconds: (q.time_limit_seconds || 30) - quizTimer,
        is_timeout: quizTimer === 0,
      }));

      const data = await OrchestrationAPI.submitZaynQuiz(levelId, sessionId, zaynData.quiz_id, formattedAnswers);
      setDecisionData(data);
      setActiveStep('decision');
      await refreshWorkflowState();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit quiz assessment.');
    } finally {
      setSubmitting(false);
    }
  };

  // Remediation trigger
  const handleRemediate = async (concept?: string) => {
    setSubmitting(true);
    setError(null);
    try {
      await OrchestrationAPI.remediate(levelId, sessionId, concept);
      await startLevel();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Remediation cycle failed.');
    } finally {
      setSubmitting(false);
    }
  };

  // Get active companion character
  const getActiveCompanion = () => {
    if (activeStep === 'nova') return AGENT_CHARACTERS.nova;
    if (activeStep === 'mira') return AGENT_CHARACTERS.mira;
    if (activeStep === 'ayan') return AGENT_CHARACTERS.ayan;
    if (activeStep === 'kira') return AGENT_CHARACTERS.kira;
    if (activeStep === 'zayn') return AGENT_CHARACTERS.zayn;
    if (activeStep === 'decision') return AGENT_CHARACTERS.elara;
    return AGENT_CHARACTERS.mira;
  };

  const currentCompanion = getActiveCompanion();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 bg-[#f8fafc]">
        <div className="text-center space-y-4 max-w-md">
          {/* Static prominent character preview during setup */}
          <img
            src="/characters/octopus.png"
            alt="Nova the Octopus"
            className="w-48 h-48 sm:w-56 sm:h-56 object-contain mx-auto"
          />
          <h2 className="text-2xl font-black text-slate-900">CLARIO Learning Engine</h2>
          <p className="text-xs text-slate-500 font-bold">
            Nova the Octopus is researching domain knowledge while Mira the Panda prepares your lesson.
          </p>
        </div>
      </div>
    );
  }

  const pipelineAgents = [
    { key: 'clario_ai', name: 'CLARIO-AI', role: 'Main Orchestrator', image: null, icon: '🤖' },
    { key: 'nova', name: 'Nova', role: 'Research Agent', image: AGENT_CHARACTERS.nova.image, icon: '🐙' },
    { key: 'mira', name: 'Mira', role: 'Teaching Agent', image: AGENT_CHARACTERS.mira.image, icon: '🐼' },
    { key: 'ayan', name: 'Ayan', role: 'Critical Thinking Agent', image: AGENT_CHARACTERS.ayan.image, icon: '🦊' },
    { key: 'kira', name: 'Kira', role: 'Real-World Agent', image: AGENT_CHARACTERS.kira.image, icon: '🐦' },
    { key: 'zayn', name: 'Zayn', role: 'Quiz Agent', image: AGENT_CHARACTERS.zayn.image, icon: '🐿️' },
    { key: 'elara', name: 'Elara', role: 'Evaluation Agent', image: AGENT_CHARACTERS.elara.image, icon: '🦅' },
  ];

  return (
    <div className="min-h-screen px-4 py-8 max-w-4xl mx-auto space-y-8 bg-[#f8fafc]">
      {/* Top Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="btn-duo-secondary px-4 py-2 text-xs font-black cursor-pointer"
        >
          ← ROADMAP
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xs font-black text-slate-500 uppercase tracking-wider">
            Level {level.level_number || 1} • {level.difficulty}
          </span>
          <span className="pill-stat pill-green text-xs">Active Companion Flow</span>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* PART 5 & 10 — CLARIO Learning Engine Workflow Visualizer                 */}
      {/* ========================================================================= */}
      <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4 pb-3 border-b-2 border-slate-100">
          <div className="flex items-center gap-2.5">
            <span className="w-8 h-8 rounded-xl bg-[#58cc02] border-b-2 border-[#46a302] text-white flex items-center justify-center text-sm font-black">
              ⚙️
            </span>
            <div>
              <h2 className="text-base font-black text-slate-900">CLARIO Learning Engine</h2>
              <p className="text-[11px] text-slate-500 font-bold">Main Orchestrator + 6 Specialized Animal Companions</p>
            </div>
          </div>
          <span className="text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full">
            Real Backend State
          </span>
        </div>

        {/* Pipeline Nodes Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5">
          {pipelineAgents.map((ag) => {
            const agState = workflowState?.agents?.[ag.key as keyof typeof workflowState.agents]?.status || 'READY';
            const badge = statusBadgeStyles[agState] || statusBadgeStyles.READY;
            const isCurrentlyActing =
              (ag.key === 'mira' && activeStep === 'mira') ||
              (ag.key === 'ayan' && activeStep === 'ayan') ||
              (ag.key === 'kira' && activeStep === 'kira') ||
              (ag.key === 'zayn' && activeStep === 'zayn') ||
              (ag.key === 'elara' && activeStep === 'decision') ||
              (ag.key === 'clario_ai');

            return (
              <div
                key={ag.key}
                className={`p-3 rounded-2xl border-2 text-center transition-all ${
                  isCurrentlyActing
                    ? 'border-emerald-300 bg-[#f0fdf4] shadow-xs ring-2 ring-emerald-200'
                    : 'border-slate-200 bg-white'
                }`}
              >
                {ag.image ? (
                  <img
                    src={ag.image}
                    alt={ag.name}
                    className="w-10 h-10 object-contain mx-auto mb-1"
                  />
                ) : (
                  <div className="text-2xl mb-1">{ag.icon}</div>
                )}
                <h4 className="text-xs font-black text-slate-900 truncate">{ag.name}</h4>
                <p className="text-[9px] text-slate-400 font-bold truncate mb-2">{ag.role.split(' ')[0]}</p>

                <span className={`inline-flex items-center gap-1 text-[9px] font-black px-2 py-0.5 rounded-full border ${badge.bg} ${badge.text} ${badge.border}`}>
                  <span>{badge.icon}</span>
                  <span className="truncate">{agState.replace('_', ' ')}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SECTION 2 & 9: LARGE PROMINENT AGENT COMPANION BANNER (180–280px HEIGHT)  */}
      {/* ========================================================================= */}
      <div className="card-duo p-6 md:p-8 flex flex-col md:flex-row items-center gap-6 md:gap-8 bg-white border-2 border-slate-200 border-b-4 border-slate-300">
        <div className="shrink-0 flex flex-col items-center">
          {/* Static, large, transparent illustration without animation or distortion */}
          <img
            src={currentCompanion.image}
            alt={`${currentCompanion.name} the ${currentCompanion.characterName}`}
            className="w-48 h-48 sm:w-56 sm:h-56 md:w-64 md:h-64 object-contain"
          />
        </div>
        <div className="flex-1 text-center md:text-left space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-[#15803d] text-xs font-black uppercase">
            {currentCompanion.characterSpecies} • {currentCompanion.role}
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight">
            {currentCompanion.name}
          </h2>
          <p className="text-xs md:text-sm font-extrabold uppercase tracking-wider text-slate-400">
            {currentCompanion.friendTitle}
          </p>
          <blockquote className="text-base md:text-lg font-bold text-[#15803d] italic pt-1">
            &ldquo;{currentCompanion.greeting}&rdquo;
          </blockquote>
          <p className="text-xs text-slate-500 font-medium">
            {currentCompanion.meaning}
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border-2 border-rose-200 rounded-2xl p-4 text-xs text-rose-700 font-bold flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="underline cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. MIRA — TEACHING EXPERIENCE                                             */}
      {/* ========================================================================= */}
      {activeStep === 'mira' && (
        <div className="space-y-6">
          {/* Nova Research Context Preview (Octopus) */}
          {novaResearch && novaResearch.summary && (
            <div className="bg-white rounded-3xl border-2 border-emerald-100 border-b-4 border-emerald-300 p-6 shadow-sm">
              <div className="flex items-center gap-3 mb-3">
                <img
                  src={AGENT_CHARACTERS.nova.image}
                  alt="Nova"
                  className="w-12 h-12 object-contain"
                />
                <div>
                  <h3 className="text-sm font-black text-slate-900">Nova — Research Friend</h3>
                  <p className="text-[11px] text-slate-500 font-bold">Multi-source exploration & domain foundations</p>
                </div>
              </div>
              <p className="text-xs text-slate-600 font-medium leading-relaxed bg-[#f8fafc] p-3.5 rounded-2xl border border-slate-200">
                {novaResearch.summary}
              </p>

              {novaResearch.sources && novaResearch.sources.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2 items-center">
                  <span className="text-[10px] font-black uppercase text-slate-400">Preferred Sources:</span>
                  {novaResearch.sources.map((s: any, idx: number) => (
                    <span
                      key={idx}
                      className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 truncate max-w-[220px]"
                    >
                      🔗 {s.title || s.url}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Mira Teaching Content */}
          <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-4 border-b-2 border-slate-100">
              <div className="flex items-center gap-3">
                <img
                  src={AGENT_CHARACTERS.mira.image}
                  alt="Mira the Panda"
                  className="w-12 h-12 object-contain"
                />
                <div>
                  <h2 className="text-xl font-black text-slate-900">Mira — Teaching Friend</h2>
                  <p className="text-xs text-slate-500 font-bold">Step-by-step conceptual instruction for {level.title}</p>
                </div>
              </div>
              <span className="pill-stat pill-green text-xs">Teaching Active</span>
            </div>

            {/* Structured Teaching Card: Explanation, Examples, Key Idea */}
            <div className="space-y-4">
              <div className="p-6 rounded-2xl bg-[#f8fafc] border-2 border-slate-100 text-slate-700 font-medium text-sm md:text-base leading-relaxed whitespace-pre-wrap">
                {miraLesson || 'Mira is analyzing concepts and preparing structured teaching breakdown...'}
              </div>

              {/* Interview Resource URL Banner */}
              {(miraInterviewUrl || miraLesson.includes('indiabix.com') || (level?.title && level.title.toLowerCase().includes('interview'))) && (
                <div className="p-4 rounded-2xl bg-emerald-50 border-2 border-emerald-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🎯</span>
                    <div>
                      <div className="text-xs font-black text-emerald-950 uppercase tracking-wider">
                        Official Interview Preparation Link
                      </div>
                      <div className="text-xs text-emerald-800 font-medium">
                        Practice real interview questions, MCQs & technical rounds
                      </div>
                    </div>
                  </div>
                  <a
                    href={miraInterviewUrl || "https://www.indiabix.com/"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-colors text-center shrink-0 flex items-center justify-center gap-1.5"
                  >
                    <span>Visit IndiaBIX Portal</span>
                    <span>↗</span>
                  </a>
                </div>
              )}

              {/* Clarification Box if user is confused */}
              {miraNeedsClarification && (
                <div className="p-5 rounded-2xl bg-[#fffbeb] border-2 border-amber-200 text-amber-900 space-y-2">
                  <span className="text-xs font-black uppercase tracking-wider">
                    🐼 Mira Clarification & Breakdown
                  </span>
                  <p className="text-xs md:text-sm font-medium">
                    Don&apos;t worry! Take it one piece at a time. The most important core principle is how the inputs translate into outcomes. What specific part feels unclear?
                  </p>
                </div>
              )}
            </div>

            {/* Learner Response Input */}
            <div className="pt-2 space-y-2">
              <label className="block text-xs font-black uppercase tracking-wider text-slate-700">
                Your Thoughts or Clarification Request
              </label>
              <textarea
                value={miraResponseText}
                onChange={(e) => setMiraResponseText(e.target.value)}
                className="w-full rounded-2xl border-2 border-slate-200 p-4 text-slate-800 text-sm font-medium focus:outline-none focus:border-[#58cc02] transition"
                rows={2}
                placeholder="Share your takeaway or ask a clarifying question..."
              />
            </div>

            {/* Interactive Actions: I Understand vs I'm Confused */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                onClick={() => setMiraNeedsClarification(true)}
                className="btn-duo-secondary flex-1 py-3.5 text-xs font-black tracking-wider cursor-pointer"
              >
                ❓ I&apos;M CONFUSED / NEED CLARIFICATION
              </button>
              <button
                type="button"
                onClick={handleMiraSubmit}
                disabled={submitting}
                className="btn-duo-green flex-2 py-3.5 text-xs font-black tracking-wider cursor-pointer"
              >
                {submitting ? 'RECORDING INTERACTION...' : '✓ I UNDERSTAND • PROCEED TO AYAN 🦊 →'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 4. AYAN — CRITICAL THINKING EXPERIENCE (FOX)                              */}
      {/* ========================================================================= */}
      {activeStep === 'ayan' && (
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b-2 border-slate-100">
            <div className="flex items-center gap-3">
              <img
                src={AGENT_CHARACTERS.ayan.image}
                alt="Ayan the Fox"
                className="w-12 h-12 object-contain"
              />
              <div>
                <h2 className="text-xl font-black text-slate-900">Ayan — Thinking Friend</h2>
                <p className="text-xs text-slate-500 font-bold">Clever reasoning, edge-cases, and causality</p>
              </div>
            </div>
            <span className="pill-stat pill-xp text-xs">Critical Thinking</span>
          </div>

          <p className="text-xs text-slate-600 font-medium bg-[#fff7ed] p-3.5 rounded-2xl border border-orange-200">
            🦊 <strong>Ayan asks you to THINK, not just memorize:</strong> &ldquo;Why would this happen? What trade-offs arise? What would you change under constraints?&rdquo;
          </p>

          <div className="space-y-6">
            {ayanData.questions.map((q: any, idx: number) => (
              <div key={q.question_id || idx} className="p-5 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 space-y-3">
                <span className="text-[11px] font-black uppercase tracking-wider text-[#d97706]">
                  Thinking Challenge {idx + 1} • {q.target_concept || 'Reasoning'}
                </span>
                <p className="text-sm md:text-base font-extrabold text-slate-900">{q.text}</p>
                <textarea
                  value={ayanAnswers[q.question_id] || ''}
                  onChange={(e) => setAyanAnswers({ ...ayanAnswers, [q.question_id]: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 p-3.5 text-sm text-slate-800 font-medium focus:outline-none focus:border-[#ff9600] transition"
                  placeholder="Explain your deductive reasoning and trade-offs..."
                  rows={3}
                />
              </div>
            ))}
          </div>

          <button
            onClick={handleAyanSubmit}
            disabled={submitting}
            className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
          >
            {submitting ? 'RECORDING THINKING...' : 'SUBMIT REASONING • PROCEED TO KIRA 🐦⬛ →'}
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 5. KIRA — REAL-WORLD APPLICATION (CROW)                                   */}
      {/* ========================================================================= */}
      {activeStep === 'kira' && (
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b-2 border-slate-100">
            <div className="flex items-center gap-3">
              <img
                src={AGENT_CHARACTERS.kira.image}
                alt="Kira the Crow"
                className="w-12 h-12 object-contain"
              />
              <div>
                <h2 className="text-xl font-black text-slate-900">Kira — Real-World Friend</h2>
                <p className="text-xs text-slate-500 font-bold">Practical application & concrete implementation</p>
              </div>
            </div>
            <span className="pill-stat pill-badge text-xs">Real-World Transfer</span>
          </div>

          <p className="text-xs text-slate-600 font-medium bg-[#f0f9ff] p-3.5 rounded-2xl border border-sky-200">
            🐦⬛ <strong>Kira tests your practical implementation:</strong> &ldquo;You are facing a realistic production scenario. What concrete solution would you deploy?&rdquo;
          </p>

          <div className="space-y-6">
            {kiraData.scenarios.map((s: any, idx: number) => (
              <div key={s.scenario_id || idx} className="p-5 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 space-y-3">
                <span className="text-[11px] font-black uppercase tracking-wider text-[#0284c7]">
                  Scenario {idx + 1} • {s.target_concept || 'Transfer'}
                </span>
                <p className="text-sm md:text-base font-extrabold text-slate-900">{s.text}</p>
                <textarea
                  value={kiraResponses[s.scenario_id] || ''}
                  onChange={(e) => setKiraResponses({ ...kiraResponses, [s.scenario_id]: e.target.value })}
                  className="w-full rounded-xl border-2 border-slate-200 p-3.5 text-sm text-slate-800 font-medium focus:outline-none focus:border-[#1cb0f6] transition"
                  placeholder="Describe your practical solution and implementation steps..."
                  rows={3}
                />
              </div>
            ))}
          </div>

          <button
            onClick={handleKiraSubmit}
            disabled={submitting}
            className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
          >
            {submitting ? 'RECORDING APPLICATION...' : 'APPLY SOLUTION • PROCEED TO ZAYN QUIZ 🐿️ →'}
          </button>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 6. ZAYN — QUIZ EXPERIENCE (SQUIRREL - 10 QUESTIONS)                        */}
      {/* ========================================================================= */}
      {activeStep === 'zayn' && zaynData.questions.length > 0 && (
        <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-6">
          <div className="flex items-center justify-between pb-4 border-b-2 border-slate-100">
            <div className="flex items-center gap-3">
              <img
                src={AGENT_CHARACTERS.zayn.image}
                alt="Zayn the Squirrel"
                className="w-12 h-12 object-contain"
              />
              <div>
                <h2 className="text-xl font-black text-slate-900">Zayn — Quiz Friend</h2>
                <p className="text-xs text-slate-500 font-bold">&ldquo;Ready? Let&apos;s test what you know.&rdquo;</p>
              </div>
            </div>
            {/* Real countdown timer */}
            <div className={`pill-stat ${quizTimer < 10 ? 'pill-streak' : 'pill-xp'}`}>
              <span>⏱️</span>
              <span>{quizTimer}s</span>
            </div>
          </div>

          {/* Question Index Progress */}
          <div className="flex items-center justify-between text-xs font-black text-slate-500">
            <span>Question {currentQuizIdx + 1} of {zaynData.questions.length}</span>
            <span className="uppercase text-[#58cc02] font-black">
              {zaynData.questions[currentQuizIdx]?.difficulty} • {zaynData.questions[currentQuizIdx]?.concept}
            </span>
          </div>

          <div className="h-3 w-full rounded-full bg-slate-100 border border-slate-200 overflow-hidden">
            <div
              className="h-full rounded-full bg-[#58cc02] transition-all duration-300"
              style={{ width: `${((currentQuizIdx + 1) / zaynData.questions.length) * 100}%` }}
            />
          </div>

          {/* Current Question Box */}
          <div className="p-6 rounded-2xl bg-[#f8fafc] border-2 border-slate-200 space-y-4">
            <h3 className="text-lg font-black text-slate-900">
              {zaynData.questions[currentQuizIdx]?.question_text}
            </h3>

            <textarea
              value={quizAnswers[zaynData.questions[currentQuizIdx]?.question_id] || ''}
              onChange={(e) => {
                const qId = zaynData.questions[currentQuizIdx]?.question_id;
                setQuizAnswers({ ...quizAnswers, [qId]: e.target.value });
              }}
              className="w-full rounded-xl border-2 border-slate-200 p-4 text-sm text-slate-800 font-medium focus:outline-none focus:border-[#58cc02] transition"
              rows={3}
              placeholder="Type your answer here..."
            />
          </div>

          {/* Question Navigation */}
          <div className="flex items-center justify-between gap-4 pt-2">
            <button
              onClick={() => setCurrentQuizIdx((i) => Math.max(0, i - 1))}
              disabled={currentQuizIdx === 0}
              className="btn-duo-secondary px-6 py-3 text-xs cursor-pointer"
            >
              ← PREVIOUS
            </button>

            {currentQuizIdx < zaynData.questions.length - 1 ? (
              <button
                onClick={() => {
                  const nextIdx = currentQuizIdx + 1;
                  setCurrentQuizIdx(nextIdx);
                  setQuizTimer(zaynData.questions[nextIdx]?.time_limit_seconds || 30);
                }}
                className="btn-duo-green px-8 py-3 text-xs cursor-pointer"
              >
                NEXT QUESTION →
              </button>
            ) : (
              <button
                onClick={handleZaynSubmit}
                disabled={submitting}
                className="btn-duo-green px-8 py-3 text-xs cursor-pointer shadow-sm"
              >
                {submitting ? 'ELARA EVALUATING EVIDENCE...' : 'SUBMIT ASSESSMENT TO ELARA 🦅 📊'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 7. ELARA — EVALUATION EXPERIENCE (EAGLE) + CLARIO-AI DECISION              */}
      {/* ========================================================================= */}
      {activeStep === 'decision' && decisionData && (
        <div className="space-y-6">
          {/* Elara Evidence Evaluation Card */}
          <div className="bg-white rounded-3xl border-2 border-slate-200 border-b-4 border-slate-300 p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between pb-4 border-b-2 border-slate-100">
              <div className="flex items-center gap-3">
                <img
                  src={AGENT_CHARACTERS.elara.image}
                  alt="Elara the Eagle"
                  className="w-12 h-12 object-contain"
                />
                <div>
                  <h2 className="text-xl font-black text-slate-900">Elara — Evaluation Friend</h2>
                  <p className="text-xs text-slate-500 font-bold">&ldquo;Let&apos;s see what you&apos;ve actually mastered.&rdquo;</p>
                </div>
              </div>
              <span className="pill-stat pill-badge text-xs">Evidence Evaluated</span>
            </div>

            {/* Concept Mastery Table / Performance Grid */}
            <div className="space-y-4">
              <h3 className="text-xs font-black uppercase tracking-wider text-slate-700">
                Evidence Breakdown Across All 4 Learning Activities
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {decisionData.concept_performances?.map((cp: any, idx: number) => {
                  const score = Math.round((cp.mastery_score || 0) * 100);
                  const isMastered = score >= 80;
                  return (
                    <div
                      key={idx}
                      className={`p-5 rounded-2xl border-2 space-y-3 ${
                        isMastered ? 'bg-[#f0fdf4] border-emerald-200' : 'bg-[#fff7ed] border-orange-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-black text-base text-slate-900">{cp.concept}</span>
                        <span className={`text-xs font-black px-2.5 py-0.5 rounded-full ${
                          isMastered ? 'bg-emerald-200 text-emerald-900' : 'bg-orange-200 text-orange-900'
                        }`}>
                          {score}% Mastery
                        </span>
                      </div>

                      {/* 4 Pillars of Evidence */}
                      <div className="grid grid-cols-2 gap-2 text-xs font-bold text-slate-600 pt-1 border-t border-slate-200/50">
                        <div>Understanding: <span className={isMastered ? 'text-emerald-700' : 'text-orange-700'}>✓ Strong</span></div>
                        <div>Reasoning: <span className={isMastered ? 'text-emerald-700' : 'text-orange-700'}>✓ Strong</span></div>
                        <div>Application: <span className={isMastered ? 'text-emerald-700' : 'text-orange-700'}>{isMastered ? '✓ Solved' : '~ Partial'}</span></div>
                        <div>Assessment: <span className={isMastered ? 'text-emerald-700' : 'text-orange-700'}>{score}%</span></div>
                      </div>

                      {cp.mistakes && cp.mistakes.length > 0 && (
                        <p className="text-[11px] text-orange-800 font-medium bg-orange-100/70 p-2 rounded-xl">
                          ⚠️ Identified gap: {cp.mistakes.join(', ')}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* CLARIO-AI — Main Orchestrator Adaptive Decision */}
          <div className="bg-white rounded-3xl border-2 border-emerald-300 border-b-6 border-emerald-500 p-8 shadow-sm space-y-6">
            <div className="text-center pb-4 border-b-2 border-slate-100">
              <span className="text-xs font-black uppercase tracking-wider text-[#15803d]">
                CLARIO-AI — Main Orchestrator
              </span>
              <h2 className="text-2xl md:text-3xl font-black text-slate-900 mt-1">
                {decisionData.decision?.decision_type === 'COMPLETE_GOAL'
                  ? 'Goal Mastered! 🏆'
                  : decisionData.decision?.decision_type === 'COMPLETE_LEVEL' || decisionData.decision?.decision_type === 'UNLOCK_NEXT_LEVEL'
                  ? 'Level Complete! Next Level Unlocked'
                  : 'Targeted Concept Remediation Needed'}
              </h2>
              <p className="text-xs text-slate-500 font-bold max-w-md mx-auto mt-1">
                {decisionData.decision?.reason}
              </p>
            </div>

            {/* Action Buttons */}
            <div>
              {decisionData.decision?.decision_type === 'COMPLETE_GOAL' ? (
                <button
                  onClick={onGoalCompleted}
                  className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
                >
                  VIEW OFFICIAL FINAL LEARNING REPORT 🏆 →
                </button>
              ) : decisionData.decision?.decision_type === 'RETEACH' ? (
                <button
                  onClick={() => handleRemediate(decisionData.decision?.target_concept)}
                  disabled={submitting}
                  className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer bg-[#ff9600] border-[#cc7800]"
                >
                  {submitting ? 'STARTING REMEDIATION...' : `REMEDIATE WEAK CONCEPT: ${decisionData.decision?.target_concept || 'CONCEPT'} 🔄`}
                </button>
              ) : (
                <button
                  onClick={onLevelCompleted}
                  className="btn-duo-green w-full py-4 text-sm tracking-wider cursor-pointer"
                >
                  CONTINUE TO NEXT ROADMAP LEVEL →
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LevelExecution;
