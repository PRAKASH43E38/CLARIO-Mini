from backend.api.routes.health import router as health_router
from backend.auth.routers import router as auth_router
from backend.api.routes.sessions import router as sessions_router
from backend.api.routes.orchestration import router as orchestration_router

__all__ = ["health_router", "auth_router", "sessions_router", "orchestration_router"]

# NOTE: the actual FastAPI app mounts routers individually in main.py.
# This file re-exports the routers for clean imports.
API_ROUTERS = (health_router, auth_router, sessions_router, orchestration_router)
