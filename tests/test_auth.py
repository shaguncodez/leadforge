import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test standard user registration returns token and user payload."""
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123",
        "role": "member",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "jane@example.com"
    assert data["user"]["name"] == "Jane Doe"
    assert data["user"]["role"] == "member"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with existing email is rejected with 400."""
    payload = {
        "name": "Alice Smith",
        "email": "duplicate@example.com",
        "password": "securepassword123",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_json_success(client: AsyncClient):
    """Test login via JSON credentials."""
    # First register
    register_payload = {
        "name": "Bob Martin",
        "email": "bob@example.com",
        "password": "mypassword123",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    # Login
    login_payload = {
        "email": "bob@example.com",
        "password": "mypassword123",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    """Test login with wrong password returns 401."""
    register_payload = {
        "name": "Charlie",
        "email": "charlie@example.com",
        "password": "correctpassword",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "charlie@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent email returns 401."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_me(client: AsyncClient, auth_headers: dict[str, str]):
    """Test GET /api/v1/auth/me returns the authenticated user."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "member@leadforge.dev"
    assert data["name"] == "Test Member"


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test GET /api/v1/auth/me without token returns 401."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
