from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityResponse
from app.services.auth_service import get_current_user
from app.services.lead_service import get_lead_by_id
from app.services.scoring_service import recalculate_and_save_lead_score

router = APIRouter(prefix="/api/v1/leads/{lead_id}/activities", tags=["Activities"])


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity_for_lead(
    lead_id: str,
    activity_in: ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a new activity for a lead and automatically recalculate lead score."""
    lead = await get_lead_by_id(db=db, lead_id=lead_id, current_user=current_user)

    activity = Activity(
        lead_id=lead.id,
        actor_id=current_user.id,
        type=activity_in.type,
        notes=activity_in.notes,
    )
    db.add(activity)
    await db.flush()

    # Recalculate score immediately
    await recalculate_and_save_lead_score(db=db, lead=lead, actor_id=current_user.id)

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="activity",
        entity_id=activity.id,
        action="create",
        details={"type": activity.type.value, "lead_id": lead.id},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(activity)

    resp = ActivityResponse.model_validate(activity)
    resp.actor_name = current_user.name
    return resp


@router.get("", response_model=List[ActivityResponse])
async def list_activities_for_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all activity logs for a lead, ordered from newest to oldest."""
    lead = await get_lead_by_id(db=db, lead_id=lead_id, current_user=current_user)

    stmt = (
        select(Activity)
        .options(selectinload(Activity.actor))
        .where(Activity.lead_id == lead.id)
        .order_by(Activity.created_at.desc())
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()

    items: List[ActivityResponse] = []
    for act in activities:
        resp = ActivityResponse.model_validate(act)
        if act.actor:
            resp.actor_name = act.actor.name
        items.append(resp)

    return items
