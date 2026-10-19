from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.analytics_service import get_analytics_summary
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/summary", response_model=Dict[str, Any])
async def get_summary_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve aggregate analytics and conversion metrics."""
    return await get_analytics_summary(db=db, current_user=current_user)
