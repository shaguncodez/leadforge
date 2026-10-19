from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Sequence, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.lead import Lead, LeadStatus
from app.schemas.lead import ScoreBreakdown


def calculate_lead_score(lead: Lead, activities: Sequence[Activity]) -> Tuple[int, ScoreBreakdown, Dict[str, Any]]:
    """
    Deterministic lead scoring (0-100) based on:
    - Purchase intent (status): new=5, contacted=15, qualified=25, proposal=35, won=35, lost=0 (max 35)
    - Engagement (activity count): 1=5pts, 2-3=10, 4-5=15, 6+=25 (max 25)
    - Profile completeness (email + company + phone): email=7, company=7, phone=6 (max 20)
    - Recency (has activity in last 7 days): 20 pts (max 20)
    """
    # 1. Purchase intent (max 35)
    intent_map = {
        LeadStatus.new: 5,
        LeadStatus.contacted: 15,
        LeadStatus.qualified: 25,
        LeadStatus.proposal: 35,
        LeadStatus.won: 35,
        LeadStatus.lost: 0,
    }
    status_enum = lead.status if isinstance(lead.status, LeadStatus) else LeadStatus(lead.status)
    purchase_intent_score = intent_map.get(status_enum, 5)

    # 2. Engagement (activity count, max 25)
    activity_count = len(activities)
    if activity_count == 0:
        engagement_score = 0
    elif activity_count == 1:
        engagement_score = 5
    elif 2 <= activity_count <= 3:
        engagement_score = 10
    elif 4 <= activity_count <= 5:
        engagement_score = 15
    else:
        engagement_score = 25

    # 3. Profile completeness (max 20)
    profile_score = 0
    present_fields = []
    if lead.email and lead.email.strip():
        profile_score += 7
        present_fields.append("email")
    if lead.company and lead.company.strip():
        profile_score += 7
        present_fields.append("company")
    if lead.phone and lead.phone.strip():
        profile_score += 6
        present_fields.append("phone")

    # 4. Recency (max 20)
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    has_recent_activity = False

    for act in activities:
        act_date = act.created_at
        if act_date.tzinfo is None:
            act_date = act_date.replace(tzinfo=timezone.utc)
        if act_date >= seven_days_ago:
            has_recent_activity = True
            break

    recency_score = 20 if has_recent_activity else 0

    # Total score calculation
    total_score = min(100, purchase_intent_score + engagement_score + profile_score + recency_score)

    breakdown = ScoreBreakdown(
        purchase_intent=purchase_intent_score,
        engagement=engagement_score,
        profile_completeness=profile_score,
        recency=recency_score,
        total=total_score,
    )

    explanation = {
        "purchase_intent": {
            "score": purchase_intent_score,
            "max": 35,
            "status": status_enum.value,
            "description": f"Status '{status_enum.value}' contributes {purchase_intent_score}/35 points based on sales pipeline stage.",
        },
        "engagement": {
            "score": engagement_score,
            "max": 25,
            "activity_count": activity_count,
            "description": f"{activity_count} logged interaction(s) contribute {engagement_score}/25 points.",
        },
        "profile_completeness": {
            "score": profile_score,
            "max": 20,
            "fields": present_fields,
            "description": f"Profile completeness ({len(present_fields)}/3 fields present: {', '.join(present_fields) if present_fields else 'none'}) contributes {profile_score}/20 points.",
        },
        "recency": {
            "score": recency_score,
            "max": 20,
            "has_recent_activity": has_recent_activity,
            "description": "Active in last 7 days (+20 points)" if has_recent_activity else "No logged activity in the last 7 days (0/20 points)",
        },
        "summary": f"Calculated LeadForge AI Score: {total_score}/100.",
    }

    return total_score, breakdown, explanation


async def recalculate_and_save_lead_score(
    db: AsyncSession,
    lead: Lead,
    actor_id: str | None = None,
) -> Tuple[int, ScoreBreakdown, Dict[str, Any]]:
    """Compute score for a lead, update lead record, and log to audit table."""
    # Fetch all activities for the lead
    stmt = (
        select(Activity)
        .where(Activity.lead_id == lead.id)
        .order_by(Activity.created_at.desc())
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()

    old_score = lead.score
    total_score, breakdown, explanation = calculate_lead_score(lead, activities)

    lead.score = total_score
    db.add(lead)

    # Add audit log
    audit_log = AuditLog(
        actor_id=actor_id,
        entity_type="lead",
        entity_id=lead.id,
        action="score_recalculated",
        details={
            "old_score": old_score,
            "new_score": total_score,
            "breakdown": breakdown.model_dump(),
        },
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(lead)

    return total_score, breakdown, explanation
