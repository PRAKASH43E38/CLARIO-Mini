import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const sessionApi = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true, // Crucial for cookie-based auth
});

export const SessionAPI = {
    async createSession() {
        const response = await sessionApi.post('/sessions');
        return response.data;
    },

    async saveInputs(sessionId: string, inputs: {
        task: string;
        goal: string;
        learner_state: string;
        interest: string;
    }) {
        const response = await sessionApi.post(`/sessions/${sessionId}/inputs`, inputs);
        return response.data;
    },

    async getSession(sessionId: string) {
        const response = await sessionApi.get(`/sessions/${sessionId}`);
        return response.data;
    },

    async getSessionInputs(sessionId: string) {
        const response = await sessionApi.get(`/sessions/${sessionId}/inputs`);
        return response.data;
    },

    async updateInputs(sessionId: string, inputs: any) {
        const response = await sessionApi.put(`/sessions/${sessionId}/inputs`, inputs);
        return response.data;
    },

    async finalizeSession(sessionId: string) {
        const response = await sessionApi.post(`/sessions/${sessionId}/finalize`);
        return response.data;
    },

    async listSessions(userId: string) {
        const response = await sessionApi.get(`/users/${userId}/sessions`);
        return response.data;
    }
};
