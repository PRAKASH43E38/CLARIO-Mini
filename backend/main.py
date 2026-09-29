import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
from backend.api.routes.rewards import router as rewards_router
from backend.auth.session import init_session_db
from backend.core.config import settings
from backend.database.connection import init_all_databases


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize persistent application storage on server boot."""
    init_all_databases()
    init_session_db()
    yield


app = FastAPI(
    title="CLARIO API",
    description="Autonomous multi-agent adaptive learning system. 'Come confused. Leave with clarity.'",
    version="0.1.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://[::1]:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://[::1]:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://[::1]:5174",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://[::1]:4173",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(orchestration_router)
app.include_router(research_router)
app.include_router(thinking_router)
app.include_router(application_router)
app.include_router(quiz_router)
app.include_router(evaluation_router)
app.include_router(adaptive_router)
app.include_router(rewards_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
