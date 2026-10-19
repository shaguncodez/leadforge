import math
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.user import RoleEnum, User
from app.schemas.lead import LeadCreate, LeadResponse, LeadUpdate
from app.services.scoring_service import calculate_lead_score, recalculate_and_save_lead_score


def check_lead_access(lead: Lead, user: User) -> None:
    """Ensure user is either the owner or an admin."""
    if user.role != RoleEnum.admin and lead.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this lead",
        )


async def create_lead(
    db: AsyncSession,
    lead_in: LeadCreate,
    current_user: User,
) -> LeadResponse:
    """Create a new lead assigned to current user, calculate initial score, and record audit log."""
    lead = Lead(
        owner_id=current_user.id,
        name=lead_in.name,
        email=lead_in.email,
        company=lead_in.company,
        phone=lead_in.phone,
        source=lead_in.source,
        status=lead_in.status,
        notes=lead_in.notes,
        score=0,
    )

    # Initial score with 0 activities
    score, _, _ = calculate_lead_score(lead, [])
    lead.score = score

    db.add(lead)
    await db.flush()

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="lead",
        entity_id=lead.id,
        action="create",
        details={"name": lead.name, "initial_score": lead.score},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(lead)

    resp = LeadResponse.model_validate(lead)
    resp.owner_name = current_user.name
    return resp


async def get_lead_by_id(
    db: AsyncSession,
    lead_id: str,
    current_user: User,
) -> Lead:
    """Fetch lead by ID, verifying ownership access."""
    stmt = (
        select(Lead)
        .options(selectinload(Lead.owner))
        .where(Lead.id == lead_id)
    )
    result = await db.execute(stmt)
    lead = result.scalar_one_or_none()

    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lead with id '{lead_id}' not found",
        )

    check_lead_access(lead, current_user)
    return lead


async def list_leads(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    per_page: int = 20,
    lead_status: Optional[LeadStatus] = None,
    source: Optional[LeadSource] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Tuple[List[LeadResponse], int, int]:
    """List leads with filtering, search, sorting, and pagination."""
    query = select(Lead).options(selectinload(Lead.owner))

    # Ownership scope: members only see their own leads, admins see all
    if current_user.role != RoleEnum.admin:
        query = query.where(Lead.owner_id == current_user.id)

    # Status filter
    if lead_status:
        query = query.where(Lead.status == lead_status)

    # Source filter
    if source:
        query = query.where(Lead.source == source)

    # Search filter
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Lead.name.ilike(term),
                Lead.email.ilike(term),
                Lead.company.ilike(term),
            )
        )

    # Count total matching
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Sorting
    valid_sort_fields = {
        "created_at": Lead.created_at,
        "updated_at": Lead.updated_at,
        "score": Lead.score,
        "name": Lead.name,
        "status": Lead.status,
    }
    sort_col = valid_sort_fields.get(sort_by, Lead.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    leads = result.scalars().all()

    items: List[LeadResponse] = []
    for l in leads:
        lead_resp = LeadResponse.model_validate(l)
        if l.owner:
            lead_resp.owner_name = l.owner.name
        items.append(lead_resp)

    pages = math.ceil(total / per_page) if per_page > 0 else 0
    return items, total, pages


async def update_lead(
    db: AsyncSession,
    lead_id: str,
    lead_update: LeadUpdate,
    current_user: User,
) -> LeadResponse:
    """Update lead details, recalculating score if status or contact fields change."""
    lead = await get_lead_by_id(db, lead_id, current_user)

    update_data = lead_update.model_dump(exclude_unset=True)
    if not update_data:
        resp = LeadResponse.model_validate(lead)
        if lead.owner:
            resp.owner_name = lead.owner.name
        return resp

    # Check if reassigning owner is allowed
    if "owner_id" in update_data and update_data["owner_id"] != lead.owner_id:
        if current_user.role != RoleEnum.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can reassign lead ownership",
            )
        lead.owner_id = update_data["owner_id"]

    for field, value in update_data.items():
        if field != "owner_id":
            setattr(lead, field, value)

    # Recalculate score with updated attributes
    await recalculate_and_save_lead_score(db, lead, actor_id=current_user.id)

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="lead",
        entity_id=lead.id,
        action="update",
        details={"updated_fields": list(update_data.keys()), "new_score": lead.score},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(lead)

    resp = LeadResponse.model_validate(lead)
    if lead.owner:
        resp.owner_name = lead.owner.name
    return resp


async def delete_lead(
    db: AsyncSession,
    lead_id: str,
    current_user: User,
) -> None:
    """Delete a lead, cascade related records, and log action."""
    lead = await get_lead_by_id(db, lead_id, current_user)

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="lead",
        entity_id=lead_id,
        action="delete",
        details={"lead_name": lead.name},
    )
    db.add(audit)
    await db.delete(lead)
    await db.commit()
