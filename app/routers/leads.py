from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.activity import Activity
from app.models.lead import LeadSource, LeadStatus
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadScoreResponse,
    LeadUpdate,
)
from app.services.auth_service import get_current_user
from app.services.lead_service import (
    create_lead,
    delete_lead,
    get_lead_by_id,
    list_leads,
    update_lead,
)
from app.services.scoring_service import calculate_lead_score, recalculate_and_save_lead_score

router = APIRouter(prefix="/api/v1/leads", tags=["Leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
async def create_new_lead(
    lead_in: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead assigned to the current user."""
    return await create_lead(db=db, lead_in=lead_in, current_user=current_user)


@router.get("", response_model=LeadListResponse)
async def get_all_leads(
    page: int = Query(default=1, ge=1, description="Page number, 1-indexed"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
    lead_status: Optional[LeadStatus] = Query(default=None, alias="status", description="Filter by status"),
    source: Optional[LeadSource] = Query(default=None, description="Filter by source"),
    search: Optional[str] = Query(default=None, description="Search by name, email, or company"),
    sort_by: str = Query(default="created_at", description="Sort by field: created_at, updated_at, score, name, status"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort direction: asc or desc"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List leads with pagination, search, status/source filters, and sorting."""
    items, total, pages = await list_leads(
        db=db,
        current_user=current_user,
        page=page,
        per_page=per_page,
        lead_status=lead_status,
        source=source,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead_details(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve detailed info for a specific lead."""
    lead = await get_lead_by_id(db=db, lead_id=lead_id, current_user=current_user)
    resp = LeadResponse.model_validate(lead)
    if lead.owner:
        resp.owner_name = lead.owner.name
    return resp


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead_details(
    lead_id: str,
    lead_update: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update lead attributes and trigger score recalculation."""
    return await update_lead(
        db=db,
        lead_id=lead_id,
        lead_update=lead_update,
        current_user=current_user,
    )


@router.delete("/{lead_id}", response_model=MessageResponse)
async def remove_lead(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a lead and all associated activities/tasks."""
    await delete_lead(db=db, lead_id=lead_id, current_user=current_user)
    return MessageResponse(message=f"Lead '{lead_id}' successfully deleted")


@router.get("/{lead_id}/score", response_model=LeadScoreResponse)
async def get_lead_score_breakdown(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the calculated score and detailed explanation breakdown for a lead."""
    lead = await get_lead_by_id(db=db, lead_id=lead_id, current_user=current_user)

    stmt = (
        select(Activity)
        .where(Activity.lead_id == lead.id)
        .order_by(Activity.created_at.desc())
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()

    score, breakdown, explanation = calculate_lead_score(lead, activities)
    return LeadScoreResponse(
        lead_id=lead.id,
        score=score,
        breakdown=breakdown,
        explanation=explanation,
    )


@router.post("/{lead_id}/score", response_model=LeadScoreResponse)
async def trigger_lead_score_recalculation(
    lead_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Force recompute lead score, persist to database, and return breakdown."""
    lead = await get_lead_by_id(db=db, lead_id=lead_id, current_user=current_user)
    score, breakdown, explanation = await recalculate_and_save_lead_score(
        db=db,
        lead=lead,
        actor_id=current_user.id,
    )
    return LeadScoreResponse(
        lead_id=lead.id,
        score=score,
        breakdown=breakdown,
        explanation=explanation,
    )
