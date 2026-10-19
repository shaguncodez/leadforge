from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.lead import Lead
from app.models.task import FollowUpTask, TaskStatus
from app.models.user import RoleEnum, User
from app.schemas.common import MessageResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.auth_service import get_current_user
from app.services.lead_service import get_lead_by_id

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new follow-up task associated with a lead."""
    # Ensure user has access to this lead
    lead = await get_lead_by_id(db=db, lead_id=task_in.lead_id, current_user=current_user)

    task = FollowUpTask(
        lead_id=lead.id,
        assignee_id=task_in.assignee_id or current_user.id,
        title=task_in.title.strip(),
        description=task_in.description,
        due_at=task_in.due_at,
        status=task_in.status,
    )
    db.add(task)
    await db.flush()

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task.id,
        action="create",
        details={"title": task.title, "lead_id": lead.id},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(task)

    resp = TaskResponse.model_validate(task)
    resp.lead_name = lead.name
    resp.assignee_name = current_user.name
    return resp


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    lead_id: Optional[str] = Query(default=None, description="Filter by lead ID"),
    assignee_id: Optional[str] = Query(default=None, description="Filter by assignee user ID"),
    task_status: Optional[TaskStatus] = Query(default=None, alias="status", description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tasks with optional filters by lead_id, assignee_id, and status."""
    query = (
        select(FollowUpTask)
        .join(FollowUpTask.lead)
        .options(selectinload(FollowUpTask.lead), selectinload(FollowUpTask.assignee))
    )

    # Access control
    if current_user.role != RoleEnum.admin:
        query = query.where(
            or_(
                Lead.owner_id == current_user.id,
                FollowUpTask.assignee_id == current_user.id,
            )
        )

    if lead_id:
        query = query.where(FollowUpTask.lead_id == lead_id)
    if assignee_id:
        query = query.where(FollowUpTask.assignee_id == assignee_id)
    if task_status:
        query = query.where(FollowUpTask.status == task_status)

    query = query.order_by(FollowUpTask.due_at.asc().nulls_last(), FollowUpTask.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()

    items: List[TaskResponse] = []
    for t in tasks:
        resp = TaskResponse.model_validate(t)
        if t.lead:
            resp.lead_name = t.lead.name
        if t.assignee:
            resp.assignee_name = t.assignee.name
        items.append(resp)

    return items


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_details(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details for a single follow-up task."""
    stmt = (
        select(FollowUpTask)
        .join(FollowUpTask.lead)
        .options(selectinload(FollowUpTask.lead), selectinload(FollowUpTask.assignee))
        .where(FollowUpTask.id == task_id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    if current_user.role != RoleEnum.admin and task.lead.owner_id != current_user.id and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    resp = TaskResponse.model_validate(task)
    if task.lead:
        resp.lead_name = task.lead.name
    if task.assignee:
        resp.assignee_name = task.assignee.name
    return resp


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task_details(
    task_id: str,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update task title, description, due date, status, or assignee."""
    stmt = (
        select(FollowUpTask)
        .join(FollowUpTask.lead)
        .options(selectinload(FollowUpTask.lead), selectinload(FollowUpTask.assignee))
        .where(FollowUpTask.id == task_id)
    )
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    if current_user.role != RoleEnum.admin and task.lead.owner_id != current_user.id and task.assignee_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    data = task_update.model_dump(exclude_unset=True)
    for field, val in data.items():
        setattr(task, field, val)

    audit = AuditLog(
        actor_id=current_user.id,
        entity_type="task",
        entity_id=task.id,
        action="update",
        details={"updated_fields": list(data.keys())},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(task)

    resp = TaskResponse.model_validate(task)
    if task.lead:
        resp.lead_name = task.lead.name
    if task.assignee:
        resp.assignee_name = task.assignee.name
    return resp


@router.delete("/{task_id}", response_model=MessageResponse)
async def remove_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a follow-up task."""
    stmt = select(FollowUpTask).join(FollowUpTask.lead).where(FollowUpTask.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found")

    if current_user.role != RoleEnum.admin and task.lead.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await db.delete(task)
    await db.commit()
    return MessageResponse(message=f"Task '{task_id}' successfully deleted")
