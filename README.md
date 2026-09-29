# CLARIO — Autonomous Adaptive Learning System

> **Tagline:** *"Come confused. Leave with clarity."*

CLARIO is an autonomous, multi-agent adaptive learning system that personalizes education from the ground up. It diagnostically understands how each individual learns, creates personalized learning roadmaps, actively teaches concepts, challenges critical thinking, tests practical real-world application, objectively evaluates mastery, and dynamically adapts or remediates whenever a learner struggles.

---

## 🏛️ Core Architecture

CLARIO strictly enforces single-responsibility orchestration:

```
USER
  ↓
AUTH & SESSION RECOVERY
  ↓
5 MIND QUESTIONS (Cognitive Profile)
  ↓
4 SESSION INPUTS (Topic, Prior Knowledge, Target Depth, Time)
  ↓
CALA ENGINE (Curriculum & Adaptive Learning Architect)
  ↓
CLARIO-AI (Central Brain & ONLY Orchestrator)
  ↓
PERSONALIZED ROADMAP & LEVEL 1 UNLOCK
  ↓
LEVEL ENTRY
  ↓
NOVA (Autonomous Research & Validation — ONLY Tavily User)
  ↓
MIRA (Tailored Concept Teaching)
  ↓
AYAN (Socratic Critical Thinking & Inquiry)
  ↓
KIRA (Real-World Applied Engineering Projects)
  ↓
ZAYN (Comprehensive Assessment Quiz)
  ↓
ELARA (Multidimensional Diagnostic Evaluation)
  ↓
CLARIO-AI ADAPTIVE DECISION
  ┌───────────────────────┬────────────────────────┐
  ↓                       ↓                        ↓
REMEDIATION             LEVEL COMPLETE           GOAL COMPLETE
(Targeted Reteach       (Unlock Next Level)      (Executive Final Report)
 + Different Retest)
```

---

## 🤖 The 7 Specialized Agents

1. **CLARIO-AI**: The **ONLY** central orchestrator. Enforces deterministic state transitions, evaluates struggle detection, and issues adaptive decisions (`COMPLETE_LEVEL`, `RETEACH`, `UNLOCK_NEXT_LEVEL`, `COMPLETE_GOAL`).
2. **Nova**: Research Agent. Validates facts, foundations, and applied methods using Tavily search.
3. **Mira**: Active Teaching Agent. Delivers clear, pedagogical lessons calibrated to the learner's cognitive style.
4. **Ayan**: Critical Thinking Agent. Challenges the learner with Socratic reasoning prompts.
5. **Kira**: Practical Application Agent. Guides hands-on, real-world scenario implementations.
6. **Zayn**: Assessment Quiz Agent. Generates calibrated 10-question evaluation quizzes.
7. **Elara**: Diagnostic Evaluation Agent. Objectively evaluates concept mastery across all agent evidence without making orchestration decisions.

---

## 💾 Exactly 3 SQLite Databases

1. **`user.db`**: User accounts, password hashes, user profiles, mind profiles, learning sessions, session inputs, CALA results.
2. **`nova.db`**: Research queries, research sources, research summaries, and validated knowledge.
3. **`clario_ai.db`**: Roadmaps, roadmap levels, level concepts, agent runs, learner responses, concept performance, Elara evaluations, adaptive decisions, remediation history, learning events, XP transactions, streaks, badges, and final reports.

---

## 🎮 Gamification Engine (Phase 15 & 16)

- **Deterministic XP**: Earned strictly via verified backend learning events:
  - Mira Teaching: `+25 XP`
  - Ayan Socratic Inquiry: `+25 XP`
  - Kira Practical Application: `+35 XP`
  - Zayn Assessment Quiz: `+40 XP`
  - Concept Mastery (≥80%): `+50 XP`
  - Completed Level: `+100 XP`
  - Remediation Overcome: `+50 XP`
  - Completed Goal: `+250 XP`
- **Consecutive Day Streaks**: Idempotently calculated once per calendar day. Resets on gaps >1 day while preserving longest streak.
- **Deterministic Badges**: Awarded for First Step, Critical Thinker, Practical Learner, Quiz Finisher, First Mastery, Level Complete, Remediation Success, Goal Complete, and Streak milestones.
- **Executive Final Learning Report**: Complete certificate with executive summary, concept scores, strengths, and PDF print capabilities upon goal completion.

---

## 🚀 Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- SQLite3

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Backend API will be live at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend UI will be live at `http://localhost:5173`.

---

## 🧪 Automated Verification Suite

Run all tests across all phases (0 through 18):
```bash
cd backend
python -m pytest tests/ -v
```

Build and typecheck frontend:
```bash
cd frontend
npm run build
```

---

## 🛡️ Security & Reliability

- **Bcrypt Password Hashing**: Cost factor 12.
- **Session Authentication**: Secure HTTP-only cookie tokens with 7-day TTL and automatic invalidation.
- **Strict Authorization**: User ownership verification on all sessions, roadmaps, evaluations, rewards, and reports.
- **SQL Injection Proof**: 100% parameterized SQLite queries.
- **Idempotent Operations**: Learning events, XP transactions, adaptive decisions, and badges are strictly idempotent (`UNIQUE` constraints).
- **Centralized LLM Fallback**: Google Gemini → Groq → OpenRouter → Mistral.
