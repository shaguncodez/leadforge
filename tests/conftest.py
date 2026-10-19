from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_db
from app.main import app
from app.models.user import RoleEnum, User
from app.services.auth_service import create_access_token, get_password_hash

# Use SQLite in-memory database for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Create all tables before each test and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for direct model manipulation in tests."""
    async with TestAsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an async HTTP test client with overridden database dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a standard member test user."""
    user = User(
        name="Test Member",
        email="member@leadforge.dev",
        password_hash=get_password_hash("password123"),
        role=RoleEnum.member,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Generate authorization headers for the test member."""
    token = create_access_token(data={"sub": test_user.id, "email": test_user.email, "role": test_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an administrator test user."""
    admin = User(
        name="Admin User",
        email="admin@leadforge.dev",
        password_hash=get_password_hash("adminpassword123"),
        role=RoleEnum.admin,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict[str, str]:
    """Generate authorization headers for the admin user."""
    token = create_access_token(data={"sub": admin_user.id, "email": admin_user.email, "role": admin_user.role.value})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second member user for ownership testing."""
    user2 = User(
        name="Other Member",
        email="other@leadforge.dev",
        password_hash=get_password_hash("otherpassword123"),
        role=RoleEnum.member,
        is_active=True,
    )
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user2)
    return user2


@pytest_asyncio.fixture
async def other_headers(other_user: User) -> dict[str, str]:
    """Generate authorization headers for the second member."""
    token = create_access_token(data={"sub": other_user.id, "email": other_user.email, "role": other_user.role.value})
    return {"Authorization": f"Bearer {token}"}
