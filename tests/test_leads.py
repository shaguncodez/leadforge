import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient, auth_headers: dict[str, str]):
    """Test creating a lead sets fields, calculates initial score, and assigns owner."""
    payload = {
        "name": "Acme Corp",
        "email": "contact@acme.com",
        "company": "Acme Industries",
        "phone": "+1-555-0100",
        "source": "web_form",
        "status": "new",
        "notes": "Interested in enterprise plan",
    }
    response = await client.post("/api/v1/leads", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Acme Corp"
    assert data["email"] == "contact@acme.com"
    assert data["company"] == "Acme Industries"
    assert data["status"] == "new"
    # Initial score: new(5) + profile (email:7 + company:7 + phone:6 = 20) = 25
    assert data["score"] == 25
    assert "id" in data
    assert data["owner_name"] == "Test Member"


@pytest.mark.asyncio
async def test_get_lead_by_id(client: AsyncClient, auth_headers: dict[str, str]):
    """Test retrieving a lead by ID."""
    create_res = await client.post(
        "/api/v1/leads",
        json={"name": "Stark Industries", "email": "tony@stark.com"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["id"]

    get_res = await client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Stark Industries"


@pytest.mark.asyncio
async def test_lead_ownership_isolation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    other_headers: dict[str, str],
    admin_headers: dict[str, str],
):
    """Test that a member cannot access or update another member's lead, but an admin can."""
    # Member 1 creates a lead
    create_res = await client.post(
        "/api/v1/leads",
        json={"name": "Wayne Enterprises", "email": "bruce@wayne.com"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["id"]

    # Member 2 attempts to get lead -> 403 Forbidden
    other_get = await client.get(f"/api/v1/leads/{lead_id}", headers=other_headers)
    assert other_get.status_code == 403

    # Member 2 attempts to update lead -> 403 Forbidden
    other_put = await client.put(
        f"/api/v1/leads/{lead_id}",
        json={"notes": "Hacked"},
        headers=other_headers,
    )
    assert other_put.status_code == 403

    # Admin CAN access lead -> 200 OK
    admin_get = await client.get(f"/api/v1/leads/{lead_id}", headers=admin_headers)
    assert admin_get.status_code == 200
    assert admin_get.json()["name"] == "Wayne Enterprises"


@pytest.mark.asyncio
async def test_update_lead(client: AsyncClient, auth_headers: dict[str, str]):
    """Test updating lead status recalculates score."""
    create_res = await client.post(
        "/api/v1/leads",
        json={"name": "Cyberdyne", "email": "sarah@cyberdyne.com", "status": "new"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["id"]
    initial_score = create_res.json()["score"]

    # Update status to qualified (adds +20 points: 5 -> 25)
    update_res = await client.put(
        f"/api/v1/leads/{lead_id}",
        json={"status": "qualified"},
        headers=auth_headers,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["status"] == "qualified"
    assert data["score"] > initial_score


@pytest.mark.asyncio
async def test_delete_lead(client: AsyncClient, auth_headers: dict[str, str]):
    """Test deleting a lead removes it permanently."""
    create_res = await client.post(
        "/api/v1/leads",
        json={"name": "Initech", "email": "peter@initech.com"},
        headers=auth_headers,
    )
    lead_id = create_res.json()["id"]

    delete_res = await client.delete(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert delete_res.status_code == 200

    # Verify deleted
    get_res = await client.get(f"/api/v1/leads/{lead_id}", headers=auth_headers)
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_pagination_and_filtering(client: AsyncClient, auth_headers: dict[str, str]):
    """Test lead pagination, status filtering, source filtering, and text search."""
    # Create multiple leads
    leads_data = [
        {"name": "Alpha Corp", "email": "alpha@test.com", "status": "new", "source": "web_form"},
        {"name": "Beta LLC", "email": "beta@test.com", "status": "contacted", "source": "referral"},
        {"name": "Gamma Inc", "email": "gamma@test.com", "status": "qualified", "source": "linkedin"},
        {"name": "Delta Co", "email": "delta@test.com", "status": "new", "source": "cold_call"},
        {"name": "Epsilon Group", "email": "epsilon@test.com", "status": "proposal", "source": "web_form"},
    ]
    for ld in leads_data:
        await client.post("/api/v1/leads", json=ld, headers=auth_headers)

    # Test pagination per_page=2
    page1 = await client.get("/api/v1/leads?page=1&per_page=2", headers=auth_headers)
    assert page1.status_code == 200
    p1_data = page1.json()
    assert len(p1_data["items"]) == 2
    assert p1_data["total"] >= 5
    assert p1_data["page"] == 1
    assert p1_data["per_page"] == 2

    # Test status filter: status=new
    status_filter = await client.get("/api/v1/leads?status=new", headers=auth_headers)
    assert status_filter.status_code == 200
    for item in status_filter.json()["items"]:
        assert item["status"] == "new"

    # Test source filter: source=referral
    source_filter = await client.get("/api/v1/leads?source=referral", headers=auth_headers)
    assert source_filter.status_code == 200
    for item in source_filter.json()["items"]:
        assert item["source"] == "referral"

    # Test text search: "Gamma"
    search_res = await client.get("/api/v1/leads?search=Gamma", headers=auth_headers)
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Gamma Inc"
