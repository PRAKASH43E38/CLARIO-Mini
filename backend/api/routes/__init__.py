from backend.api.routes.health import router as health_router
from backend.auth.routers import router as auth_router
from backend.api.routes.sessions import router as sessions_router
from backend.api.routes.orchestration import router as orchestration_router
from backend.api.routes.research import router as research_router
from backend.api.routes.thinking import router as thinking_router
from backend.api.routes.application import router as application_router
from backend.api.routes.quiz import router as quiz_router
from backend.api.routes.evaluation import router as evaluation_router
from backend.api.routes.adaptive import router as adaptive_router

__all__ = [
    "health_router",
    "auth_router",
    "sessions_router",
    "orchestration_router",
    "research_router",
    "thinking_router",
    "application_router",
    "quiz_router",
    "evaluation_router",
    "adaptive_router",
    "API_ROUTERS",
]

API_ROUTERS = (
    health_router,
    auth_router,
    sessions_router,
    orchestration_router,
    research_router,
    thinking_router,
    application_router,
    quiz_router,
    evaluation_router,
    adaptive_router,
)
