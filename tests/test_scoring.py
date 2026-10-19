from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient

from app.models.activity import Activity, ActivityType
from app.models.lead import Lead, LeadStatus
from app.services.scoring_service import calculate_lead_score


def test_deterministic_scoring_unit_minimal():
    """Test minimal lead with no contact info and no activities: new status (5 pts)."""
    lead = Lead(
        name="Minimal Lead",
        email=None,
        company=None,
        phone=None,
        status=LeadStatus.new,
    )
    score, breakdown, explanation = calculate_lead_score(lead, [])
    assert score == 5
    assert breakdown.purchase_intent == 5
    assert breakdown.engagement == 0
    assert breakdown.profile_completeness == 0
    assert breakdown.recency == 0
    assert breakdown.total == 5


def test_deterministic_scoring_unit_full_profile():
    """Test lead with full profile: email(7) + company(7) + phone(6) = 20 pts."""
    lead = Lead(
        name="Complete Lead",
        email="test@example.com",
        company="Acme Co",
        phone="555-1234",
        status=LeadStatus.new,  # 5 pts
    )
    score, breakdown, _ = calculate_lead_score(lead, [])
    # 5 (intent) + 20 (profile) = 25
    assert score == 25
    assert breakdown.profile_completeness == 20
    assert breakdown.purchase_intent == 5


def test_deterministic_scoring_engagement_tiers():
    """Test engagement tiers: 1 act=5, 2-3 acts=10, 4-5 acts=15, 6+ acts=25."""
    lead = Lead(name="Engaged Lead", status=LeadStatus.new)
    now = datetime.now(timezone.utc)
    # Old activities (> 7 days ago) to isolate engagement from recency
    old_date = now - timedelta(days=15)

    acts_1 = [Activity(type=ActivityType.call, notes="test", created_at=old_date)]
    _, b1, _ = calculate_lead_score(lead, acts_1)
    assert b1.engagement == 5
    assert b1.recency == 0

    acts_3 = [Activity(type=ActivityType.call, notes=f"test {i}", created_at=old_date) for i in range(3)]
    _, b3, _ = calculate_lead_score(lead, acts_3)
    assert b3.engagement == 10

    acts_5 = [Activity(type=ActivityType.call, notes=f"test {i}", created_at=old_date) for i in range(5)]
    _, b5, _ = calculate_lead_score(lead, acts_5)
    assert b5.engagement == 15

    acts_7 = [Activity(type=ActivityType.call, notes=f"test {i}", created_at=old_date) for i in range(7)]
    _, b7, _ = calculate_lead_score(lead, acts_7)
    assert b7.engagement == 25


def test_deterministic_scoring_recency():
    """Test recency score gives 20 pts if activity within 7 days, 0 if older."""
    lead = Lead(name="Recent Lead", status=LeadStatus.new)
    now = datetime.now(timezone.utc)

    # Activity from 2 days ago
    recent_acts = [Activity(type=ActivityType.email, notes="recent", created_at=now - timedelta(days=2))]
    _, b_recent, _ = calculate_lead_score(lead, recent_acts)
    assert b_recent.recency == 20

    # Activity from 10 days ago
    past_acts = [Activity(type=ActivityType.email, notes="past", created_at=now - timedelta(days=10))]
    _, b_past, _ = calculate_lead_score(lead, past_acts)
    assert b_past.recency == 0


def test_deterministic_scoring_perfect_100():
    """Test proposal stage (35) + 6 activities (25) + complete profile (20) + recent (20) = 100."""
    lead = Lead(
        name="Hot Prospect",
        email="vip@enterprise.com",
        company="Global Corp",
        phone="+1-800-555-9999",
        status=LeadStatus.proposal,  # 35
    )
    now = datetime.now(timezone.utc)
    activities = [
        Activity(type=ActivityType.meeting, notes=f"Meeting {i}", created_at=now - timedelta(days=i))
        for i in range(6)
    ]
    score, breakdown, explanation = calculate_lead_score(lead, activities)
    assert score == 100
    assert breakdown.purchase_intent == 35
    assert breakdown.engagement == 25
    assert breakdown.profile_completeness == 20
    assert breakdown.recency == 20
    assert "purchase_intent" in explanation
    assert "engagement" in explanation
    assert "profile_completeness" in explanation
    assert "recency" in explanation


@pytest.mark.asyncio
async def test_score_api_endpoint(client: AsyncClient, auth_headers: dict[str, str]):
    """Test GET /api/v1/leads/{lead_id}/score endpoint returns full breakdown and explanation."""
    create_res = await client.post(
        "/api/v1/leads",
        json={
            "name": "Omega Systems",
            "email": "info@omega.com",
            "company": "Omega Tech",
            "phone": "555-9876",
            "status": "qualified",  # 25 intent
        },
        headers=auth_headers,
    )
    lead_id = create_res.json()["id"]

    # Initial score check via API: 25 (qualified) + 20 (profile) = 45
    score_res = await client.get(f"/api/v1/leads/{lead_id}/score", headers=auth_headers)
    assert score_res.status_code == 200
    score_data = score_res.json()
    assert score_data["score"] == 45
    assert score_data["breakdown"]["purchase_intent"] == 25
    assert score_data["breakdown"]["profile_completeness"] == 20
    assert score_data["breakdown"]["engagement"] == 0
    assert score_data["breakdown"]["recency"] == 0
    assert "explanation" in score_data

    # Add an activity: should boost engagement (+5) AND recency (+20) -> score becomes 45 + 25 = 70
    act_res = await client.post(
        f"/api/v1/leads/{lead_id}/activities",
        json={"type": "call", "notes": "Introductory discovery call completed"},
        headers=auth_headers,
    )
    assert act_res.status_code == 201

    # Check updated lead score
    updated_lead = await client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert updated_lead.json()["score"] == 70

    # Verify score explanation endpoint matches
    score_res2 = await client.get(f"/api/v1/leads/{lead_id}/score", headers=auth_headers)
    assert score_res2.status_code == 200
    s2_data = score_res2.json()
    assert s2_data["score"] == 70
    assert s2_data["breakdown"]["engagement"] == 5
    assert s2_data["breakdown"]["recency"] == 20
