import React, { useEffect, useState } from 'react';
import { Landing } from './pages/Landing';
import { AuthPage } from './pages/AuthPage';
import type { AuthResult } from './pages/AuthPage';
import { ProfileSetup } from './pages/ProfileSetup';
import { MindQuestions } from './pages/MindQuestions';
import { Home } from './pages/Home';
import InputForm from './pages/SessionFlow/InputForm';
import ReviewScreen from './pages/SessionFlow/ReviewScreen';
import RoadmapView from './pages/LearningFlow/RoadmapView';
import LevelExecution from './pages/LearningFlow/LevelExecution';
import JourneyDashboard from './pages/LearningFlow/JourneyDashboard';
import { FinalReportView } from './pages/LearningFlow/FinalReportView';
import { RewardsWidget } from './components/RewardsWidget';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Step =
  | 'landing'
  | 'register'
  | 'login'
  | 'profile'
  | 'mind-questions'
  | 'home'
  | 'session-inputs'
  | 'session-review'
  | 'roadmap'
  | 'level-execution'
  | 'journey-dashboard'
  | 'final-report';

type ProfileDestination = 'mind-questions' | 'home';

interface User {
  user_id: string;
  email: string;
  name: string;
}

interface SessionResponse extends User {
  mind_profile_completed: boolean;
}

interface ActiveLevel {
  level_id: string;
  title: string;
  objective: string;
  difficulty: string;
  level_number?: number;
  status?: string;
}

function isSessionResponse(value: unknown): value is SessionResponse {
  if (typeof value !== 'object' || value === null) return false;
  return 'user_id' in value
    && typeof value.user_id === 'string'
    && 'email' in value
    && typeof value.email === 'string'
    && 'name' in value
    && typeof value.name === 'string'
    && 'mind_profile_completed' in value
    && typeof value.mind_profile_completed === 'boolean';
}

export const App: React.FC = () => {
  const [step, setStep] = useState<Step>('landing');
  const [user, setUser] = useState<User | null>(null);
  const [profileDestination, setProfileDestination] =
    useState<ProfileDestination>('mind-questions');
  const [editingMindProfile, setEditingMindProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    return localStorage.getItem('clario_active_session');
  });
  const [activeLevel, setActiveLevel] = useState<ActiveLevel | null>(() => {
    const saved = localStorage.getItem('clario_active_level');
    return saved ? JSON.parse(saved) : null;
  });

  // Track session storage for recovery
  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem('clario_active_session', activeSessionId);
    } else {
      localStorage.removeItem('clario_active_session');
    }
  }, [activeSessionId]);

  useEffect(() => {
    if (activeLevel) {
      localStorage.setItem('clario_active_level', JSON.stringify(activeLevel));
    } else {
      localStorage.removeItem('clario_active_level');
    }
  }, [activeLevel]);

  useEffect(() => {
    let active = true;
    fetch(`${API}/auth/me`, { credentials: 'include' })
      .then(async (response) => {
        if (response.status === 401) return null;
        const data: unknown = await response.json();
        if (!response.ok) throw new Error('Could not restore your session.');
        if (!isSessionResponse(data)) throw new Error('The server returned invalid session information.');
        return data;
      })
      .then((session) => {
        if (!active || !session) return;
        setUser({
          user_id: session.user_id,
          email: session.email,
          name: session.name,
        });

        // Recover saved step if user was actively learning
        const savedStep = localStorage.getItem('clario_active_step') as Step | null;
        if (
          savedStep &&
          ['roadmap', 'level-execution', 'journey-dashboard', 'final-report'].includes(savedStep) &&
          localStorage.getItem('clario_active_session')
        ) {
          setStep(savedStep);
        } else {
          setStep(session.mind_profile_completed ? 'home' : 'profile');
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : 'Could not restore your session.');
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const navigateTo = (nextStep: Step) => {
    localStorage.setItem('clario_active_step', nextStep);
    setStep(nextStep);
  };

  const handleAuth = (result: AuthResult) => {
    setUser({ user_id: result.user_id, email: result.email, name: result.name });
    setProfileDestination('mind-questions');
    setEditingMindProfile(false);
    navigateTo(result.mind_profile_completed ? 'home' : 'profile');
  };

  const handleLogout = async () => {
    setError(null);
    try {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Ignore network errors on logout
    }
    setUser(null);
    setActiveSessionId(null);
    setActiveLevel(null);
    localStorage.removeItem('clario_active_session');
    localStorage.removeItem('clario_active_level');
    localStorage.removeItem('clario_active_step');
    navigateTo('landing');
  };

  const handleEnterLevel = (_levelId: string, sessionId: string, level: ActiveLevel) => {
    setActiveSessionId(sessionId);
    setActiveLevel(level);
    navigateTo('level-execution');
  };

  const isLearningFlow = [
    'session-inputs',
    'session-review',
    'roadmap',
    'level-execution',
    'journey-dashboard',
    'final-report',
  ].includes(step);

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans">
      {/* Global Navigation Header when user is logged in */}
      {user && step !== 'landing' && step !== 'register' && step !== 'login' && (
        <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b-2 border-slate-200 px-4 sm:px-8 py-3 flex items-center justify-between shadow-[0_2px_4px_rgba(0,0,0,0.02)]">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigateTo('home')}
              className="flex items-center gap-2.5 group text-left cursor-pointer"
            >
              <div className="w-10 h-10 rounded-2xl bg-[#58cc02] border-b-4 border-[#46a302] flex items-center justify-center text-white font-black text-xl shadow-sm group-hover:scale-105 active:scale-95 transition">
                C
              </div>
              <div className="hidden sm:block">
                <span className="text-lg font-black tracking-tight text-[#46a302] group-hover:text-[#58cc02] transition">
                  CLARIO
                </span>
                <p className="text-[11px] text-slate-500 font-bold">Come confused. Leave with clarity.</p>
              </div>
            </button>

            {isLearningFlow && activeSessionId && (
              <div className="hidden md:flex items-center gap-2 pl-4 border-l-2 border-slate-200 text-xs">
                <button
                  onClick={() => navigateTo('roadmap')}
                  className={`px-3 py-1.5 rounded-xl transition font-bold cursor-pointer ${
                    step === 'roadmap' ? 'bg-[#dcfce7] text-[#15803d] border-b-2 border-[#86efac]' : 'text-slate-600 hover:text-emerald-700 hover:bg-emerald-50'
                  }`}
                >
                  🗺️ Roadmap
                </button>
                <button
                  onClick={() => navigateTo('journey-dashboard')}
                  className={`px-3 py-1.5 rounded-xl transition font-bold cursor-pointer ${
                    step === 'journey-dashboard' ? 'bg-[#dcfce7] text-[#15803d] border-b-2 border-[#86efac]' : 'text-slate-600 hover:text-emerald-700 hover:bg-emerald-50'
                  }`}
                >
                  📊 Dashboard
                </button>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Real Rewards Widget (XP, Streak, Badges) */}
            <RewardsWidget />

            <div className="h-6 w-px bg-slate-200 hidden sm:block" />

            <button
              onClick={handleLogout}
              className="text-xs text-slate-500 hover:text-rose-600 font-bold px-3 py-1.5 rounded-xl hover:bg-rose-50 transition border border-transparent hover:border-rose-200 cursor-pointer"
              title="Log out"
            >
              Log out
            </button>
          </div>
        </header>
      )}

      {error && (
        <div className="bg-rose-50 border-b-2 border-rose-200 text-rose-700 text-xs px-4 py-2.5 text-center font-bold flex items-center justify-center gap-2">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="underline hover:text-rose-900 ml-2 cursor-pointer">
            Dismiss
          </button>
        </div>
      )}

      {/* Pages Routing */}
      {step === 'landing' && (
        <Landing
          onStart={() => navigateTo('login')}
        />
      )}

      {(step === 'register' || step === 'login') && (
        <AuthPage
          mode={step}
          onComplete={handleAuth}
          onSwitchMode={() => navigateTo(step === 'register' ? 'login' : 'register')}
        />
      )}

      {step === 'profile' && user && (
        <ProfileSetup
          user={user}
          onComplete={(name) => {
            setUser({ ...user, name });
            navigateTo(profileDestination);
          }}
        />
      )}

      {step === 'mind-questions' && user && (
        <MindQuestions
          user={user}
          editing={editingMindProfile}
          onComplete={() => {
            setEditingMindProfile(false);
            navigateTo('home');
          }}
        />
      )}

      {step === 'home' && user && (
        <Home
          user={user}
          onLogout={handleLogout}
          onEditProfile={() => {
            setProfileDestination('home');
            navigateTo('profile');
          }}
          onEditMindProfile={() => {
            setEditingMindProfile(true);
            navigateTo('mind-questions');
          }}
          onStartLearning={(sessionId) => {
            setActiveSessionId(sessionId);
            navigateTo('session-inputs');
          }}
          onResumeSession={(sessionId) => {
            setActiveSessionId(sessionId);
            navigateTo('roadmap');
          }}
        />
      )}

      {step === 'session-inputs' && user && activeSessionId && (
        <InputForm
          sessionId={activeSessionId}
          onBack={() => navigateTo('home')}
          onComplete={() => navigateTo('session-review')}
        />
      )}

      {step === 'session-review' && user && activeSessionId && (
        <ReviewScreen
          sessionId={activeSessionId}
          onEdit={() => navigateTo('session-inputs')}
          onComplete={() => navigateTo('roadmap')}
        />
      )}

      {step === 'roadmap' && user && activeSessionId && (
        <RoadmapView
          sessionId={activeSessionId}
          userId={user.user_id}
          onBack={() => navigateTo('home')}
          onEnterLevel={handleEnterLevel}
        />
      )}

      {step === 'level-execution' && user && activeSessionId && activeLevel && (
        <LevelExecution
          sessionId={activeSessionId}
          levelId={activeLevel.level_id}
          level={activeLevel}
          onBack={() => navigateTo('roadmap')}
          onLevelCompleted={() => navigateTo('roadmap')}
          onGoalCompleted={() => navigateTo('final-report')}
        />
      )}

      {step === 'journey-dashboard' && user && activeSessionId && (
        <JourneyDashboard
          sessionId={activeSessionId}
          onBack={() => navigateTo('roadmap')}
          onStartNewSession={() => {
            setActiveSessionId(null);
            setActiveLevel(null);
            navigateTo('home');
          }}
        />
      )}

      {step === 'final-report' && user && activeSessionId && (
        <FinalReportView
          sessionId={activeSessionId}
          onBackToRoadmap={() => navigateTo('roadmap')}
          onStartNewSession={() => {
            setActiveSessionId(null);
            setActiveLevel(null);
            navigateTo('home');
          }}
        />
      )}
    </div>
  );
};

export default App;
