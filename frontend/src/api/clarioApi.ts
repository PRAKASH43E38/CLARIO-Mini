import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

// ─── Orchestration / Loop API ────────────────────────────────────────────────

export const OrchestrationAPI = {
    /** Initialize journey: CALA → Roadmap → Level 1 Unlock */
    async initializeLoop(sessionId?: string) {
        const payload = sessionId ? { session_id: sessionId } : {};
        const response = await api.post('/orchestration/loop/initialize', payload);
        return response.data;
    },

    /** Enter a specific level */
    async enterLevel(levelId: string, sessionId?: string) {
        const params = sessionId ? `?session_id=${sessionId}` : '';
        const response = await api.post(`/orchestration/loop/enter-level/${levelId}${params}`);
        return response.data;
    },

    /** Execute full level flow: Nova → Mira → Ayan → Kira → Zayn → Elara → Decision */
    async runLevel(levelId: string, sessionId: string, simulatedAnswers?: Record<string, any>) {
        const response = await api.post(`/orchestration/loop/run-level/${levelId}`, {
            session_id: sessionId,
            simulated_answers: simulatedAnswers,
        });
        return response.data;
    },

    /** Execute remediation cycle for a weak concept */
    async remediate(levelId: string, sessionId: string, concept?: string, retestScore?: number) {
        const response = await api.post(`/orchestration/loop/remediate-cycle/${levelId}`, {
            session_id: sessionId,
            concept: concept || null,
            simulated_retest_score: retestScore ?? 0.92,
        });
        return response.data;
    },

    /** Get complete live journey status */
    async getJourneyStatus(sessionId: string) {
        const response = await api.get(`/orchestration/loop/status/${sessionId}`);
        return response.data;
    },

    /** Get final learning report for a completed session */
    async getFinalReport(sessionId: string) {
        const response = await api.get(`/orchestration/loop/final-report/${sessionId}`);
        return response.data;
    },

    // ─── Real Step-by-Step Interactive Workflow ─────────────────────────────

    /** Start interactive level: Nova research + Mira lesson */
    async startStep(levelId: string, sessionId: string) {
        const response = await api.post(`/orchestration/step/start/${levelId}`, {
            session_id: sessionId
        });
        return response.data;
    },

    /** Complete Mira reading and trigger Ayan thinking challenges */
    async submitMiraComplete(levelId: string, sessionId: string, responseText?: string) {
        const response = await api.post(`/orchestration/step/mira-complete/${levelId}`, {
            session_id: sessionId,
            response_text: responseText || "Understood foundational concepts."
        });
        return response.data;
    },

    /** Submit Socratic thinking answers to Ayan and trigger Kira application */
    async submitAyanThinking(levelId: string, sessionId: string, challengeId: string, answers: Record<string, string>) {
        const response = await api.post(`/orchestration/step/ayan-submit/${levelId}`, {
            session_id: sessionId,
            challenge_id: challengeId,
            answers
        });
        return response.data;
    },

    /** Submit real-world practical solutions to Kira and trigger Zayn 10-question assessment */
    async submitKiraApplication(levelId: string, sessionId: string, scenarioId: string, responses: Record<string, string>) {
        const response = await api.post(`/orchestration/step/kira-submit/${levelId}`, {
            session_id: sessionId,
            scenario_id: scenarioId,
            responses
        });
        return response.data;
    },

    /** Submit Zayn quiz answers -> triggers Elara evaluation & CLARIO-AI adaptive decision */
    async submitZaynQuiz(levelId: string, sessionId: string, quizId: string, answers: Array<Record<string, any>>) {
        const response = await api.post(`/orchestration/step/zayn-submit/${levelId}`, {
            session_id: sessionId,
            quiz_id: quizId,
            answers
        });
        return response.data;
    },

    /** Get real-time workflow engine state for all 6 agents + CLARIO-AI */
    async getStepState(levelId: string, sessionId: string) {
        const response = await api.get(`/orchestration/step/state/${levelId}?session_id=${sessionId}`);
        return response.data;
    },
};

// ─── Teaching API ────────────────────────────────────────────────────────────

export const TeachingAPI = {
    async getTeaching(sessionId: string, levelId: string) {
        const response = await api.get(`/teaching/${sessionId}/${levelId}`);
        return response.data;
    },
};

// ─── Thinking API ────────────────────────────────────────────────────────────

export const ThinkingAPI = {
    async getThinking(sessionId: string, levelId: string) {
        const response = await api.get(`/thinking/${sessionId}/${levelId}`);
        return response.data;
    },

    async submitThinkingResponse(payload: {
        session_id: string;
        question_id: string;
        user_answer: string;
    }) {
        const response = await api.post('/thinking/respond', payload);
        return response.data;
    },
};

// ─── Application API ────────────────────────────────────────────────────────

export const ApplicationAPI = {
    async getApplication(sessionId: string, levelId: string) {
        const response = await api.get(`/application/${sessionId}/${levelId}`);
        return response.data;
    },

    async submitApplicationResponse(payload: {
        session_id: string;
        scenario_id: string;
        user_response: string;
    }) {
        const response = await api.post('/application/respond', payload);
        return response.data;
    },
};

// ─── Quiz API ────────────────────────────────────────────────────────────────

export const QuizAPI = {
    async getQuiz(sessionId: string, levelId: string) {
        const response = await api.get(`/quiz/${sessionId}/${levelId}`);
        return response.data;
    },

    async submitQuizAnswer(payload: {
        session_id: string;
        quiz_id: string;
        question_id: string;
        answer: string;
        response_time_seconds: number;
        is_timeout: boolean;
    }) {
        const response = await api.post('/quiz/submit', payload);
        return response.data;
    },
};

// ─── Evaluation API ──────────────────────────────────────────────────────────

export const EvaluationAPI = {
    async getEvaluation(sessionId: string, levelId: string) {
        const response = await api.get(`/evaluation/${sessionId}/${levelId}`);
        return response.data;
    },
};

// ─── Adaptive Decision API ───────────────────────────────────────────────────

export const AdaptiveAPI = {
    async getDecision(sessionId: string, levelId: string) {
        const response = await api.get(`/adaptive/${sessionId}/${levelId}`);
        return response.data;
    },

    async getConcepts(sessionId: string, levelId: string) {
        const response = await api.get(`/adaptive/${sessionId}/${levelId}/concepts`);
        return response.data;
    },
};

// ─── Rewards & Gamification API (Phase 15/16) ────────────────────────────────

export interface RewardSummary {
    user_id: string;
    total_xp: number;
    level: number;
    streak: {
        current_streak: number;
        longest_streak: number;
        last_learning_date: string | null;
    };
    earned_badges: Array<{
        badge_key: string;
        badge_name: string;
        description: string;
        icon: string;
        awarded_at: string;
    }>;
    badge_count: number;
    recent_xp: Array<{
        transaction_id: string;
        xp_amount: number;
        reason: string;
        created_at: string;
    }>;
}

export interface BadgeItem {
    badge_key: string;
    badge_name: string;
    description: string;
    icon: string;
    earned: boolean;
    awarded_at: string | null;
}

export interface FinalReportData {
    report_id: string;
    session_id: string;
    user_id: string;
    topic: string;
    total_levels: number;
    completed_levels: number;
    total_xp: number;
    mastered_concepts: Array<{
        concept: string;
        mastery_score: number;
        status: string;
        understanding: string;
        reasoning: string;
    }>;
    remediations_count: number;
    executive_summary: string;
    strengths: string[];
    growth_areas: string[];
    created_at: string;
}

export const RewardsAPI = {
    async getRewards(): Promise<RewardSummary> {
        const response = await api.get('/rewards');
        return response.data;
    },

    async getXp() {
        const response = await api.get('/rewards/xp');
        return response.data;
    },

    async getStreak() {
        const response = await api.get('/rewards/streak');
        return response.data;
    },

    async getBadges(): Promise<{
        user_id: string;
        earned_count: number;
        total_available: number;
        badges: BadgeItem[];
    }> {
        const response = await api.get('/rewards/badges');
        return response.data;
    },
};

