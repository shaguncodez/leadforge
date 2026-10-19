from typing import Any, Dict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.task import FollowUpTask, TaskStatus
from app.models.user import RoleEnum, User


async def get_analytics_summary(db: AsyncSession, current_user: User) -> Dict[str, Any]:
    """Calculate aggregated metrics for dashboard."""
    # Scope by user role
    leads_filter = []
    if current_user.role != RoleEnum.admin:
        leads_filter.append(Lead.owner_id == current_user.id)

    # Total leads
    total_stmt = select(func.count(Lead.id)).where(*leads_filter)
    total_leads = (await db.execute(total_stmt)).scalar_one() or 0

    # Leads by status
    by_status_stmt = (
        select(Lead.status, func.count(Lead.id))
        .where(*leads_filter)
        .group_by(Lead.status)
    )
    by_status_res = (await db.execute(by_status_stmt)).all()
    # Initialize all statuses to 0
    by_status = {status.value: 0 for status in LeadStatus}
    for status_val, count in by_status_res:
        key = status_val.value if isinstance(status_val, LeadStatus) else str(status_val)
        by_status[key] = count

    # Leads by source
    by_source_stmt = (
        select(Lead.source, func.count(Lead.id))
        .where(*leads_filter)
        .group_by(Lead.source)
    )
    by_source_res = (await db.execute(by_source_stmt)).all()
    by_source = {src.value: 0 for src in LeadSource}
    for src_val, count in by_source_res:
        key = src_val.value if isinstance(src_val, LeadSource) else str(src_val)
        by_source[key] = count

    # Average score
    avg_stmt = select(func.avg(Lead.score)).where(*leads_filter)
    avg_score_raw = (await db.execute(avg_stmt)).scalar_one()
    avg_score = round(float(avg_score_raw), 1) if avg_score_raw is not None else 0.0

    # Conversion rate: Won leads / Total leads * 100
    won_leads = by_status.get(LeadStatus.won.value, 0)
    conversion_rate = round((won_leads / total_leads * 100), 1) if total_leads > 0 else 0.0

    # Total activities
    if current_user.role == RoleEnum.admin:
        act_stmt = select(func.count(Activity.id))
    else:
        act_stmt = select(func.count(Activity.id)).join(Lead).where(Lead.owner_id == current_user.id)
    total_activities = (await db.execute(act_stmt)).scalar_one() or 0

    # Pending tasks
    if current_user.role == RoleEnum.admin:
        task_stmt = select(func.count(FollowUpTask.id)).where(FollowUpTask.status == TaskStatus.pending)
    else:
        task_stmt = (
            select(func.count(FollowUpTask.id))
            .join(Lead)
            .where(Lead.owner_id == current_user.id, FollowUpTask.status == TaskStatus.pending)
        )
    pending_tasks = (await db.execute(task_stmt)).scalar_one() or 0

    return {
        "total_leads": total_leads,
        "by_status": by_status,
        "by_source": by_source,
        "avg_score": avg_score,
        "conversion_rate": conversion_rate,
        "total_activities": total_activities,
        "pending_tasks": pending_tasks,
    }
