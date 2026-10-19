from app.routers.auth import router as auth_router
from app.routers.leads import router as leads_router
from app.routers.activities import router as activities_router
from app.routers.tasks import router as tasks_router
from app.routers.analytics import router as analytics_router

__all__ = [
    "auth_router",
    "leads_router",
    "activities_router",
    "tasks_router",
    "analytics_router",
]
