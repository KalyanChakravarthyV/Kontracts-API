"""
Pytest configuration and fixtures.

This module provides shared fixtures and configuration for all tests.
Following PostgreSQL best practices:
    - Use PostgreSQL database from tests/.env.test file
- Rollback transactions after each test
- Isolate test data
- Use Alembic migrations for test database setup
"""

import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv

# Load test environment variables from tests/.env.test before testcontainers import.
test_env_path = Path(__file__).parent / ".env.test"
load_dotenv(dotenv_path=test_env_path, override=True)

# Disable Ryuk to keep the container running after pytest exits.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
os.environ.setdefault("TESTCONTAINERS_REUSE_ENABLE", "true")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
from fastapi.testclient import TestClient
from fastapi.security import SecurityScopes, HTTPAuthorizationCredentials, HTTPBearer
from alembic import command
from alembic.config import Config
from testcontainers.postgres import PostgresContainer

from app.database import Base, get_db
from app.main import app
from app.models.lease import Lease, LeaseScheduleEntry, LeaseClassification
from app.models.schedule import ASC842Schedule, IFRS16Schedule
from app.models.user import Users
from app.models.journals import (
    JournalEntries,
    JournalEntrySetups,
    Payments,
    Documents,
)
from app.api.v1.leases import auth as leases_auth
from app.api.v1.schedules import auth as schedules_auth
from app.api.v1.payments import auth as payments_auth

def _env_truthy(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.lower() in ("1", "true", "yes")


TEST_PRESERVE_DB = _env_truthy(os.getenv("TEST_PRESERVE_DB"), default=True)

_pg_container = None


@pytest.fixture(scope="session")
def postgres_container():
    """
    Start a persistent PostgreSQL container for tests.

    Container settings are loaded from tests/.env.test.
    """
    if not test_env_path.exists():
        raise ValueError(
            "tests/.env.test not found.\n"
            "Please create tests/.env.test with TEST_POSTGRES_* values."
        )

    global _pg_container
    if _pg_container is not None:
        yield _pg_container
        return

    image = os.getenv("TEST_POSTGRES_IMAGE", "postgres:17-alpine")
    dbname = os.getenv("TEST_POSTGRES_DB", "Kontracts_test")
    user = os.getenv("TEST_POSTGRES_USER", "kontracts_user")
    password = os.getenv("TEST_POSTGRES_PASSWORD", "kontracts_user_pwd")

    os.environ.setdefault("TESTCONTAINERS_REUSE_ENABLE", "true")

    _pg_container = PostgresContainer(
        image=image,
        username=user,
        password=password,
        dbname=dbname,
    )
    _pg_container.start()
    yield _pg_container


@pytest.fixture(scope="session")
def database_url(postgres_container):
    """Return the container's connection URL for the test database."""
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def engine(database_url):
    """
    Create a test database engine.

    Scope: session - created once per test session
    PostgreSQL best practice: Use a separate test database

    This connects to the PostgreSQL database from the ephemeral container
    """
    # Create engine
    test_engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,  # Verify connections before using
    )

    # Create kontracts schema
    with test_engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS kontracts"))

    # Run Alembic migrations to set up the database schema
    os.environ["DATABASE_URL"] = database_url
    os.environ["SCHEMA_NAME"] = "kontracts"
    alembic_cfg = Config(str(Path(__file__).parent / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[1] / "alembic"),
    )

    # Run migrations
    command.upgrade(alembic_cfg, "head")

    yield test_engine

    # Cleanup: drop all tables, types, and schema after entire test session
    if not TEST_PRESERVE_DB:
        with test_engine.begin() as conn:
            # Drop the schema with all its contents
            conn.execute(text("DROP SCHEMA IF EXISTS kontracts CASCADE"))
            # Drop enum types that may have been created in public schema
            conn.execute(text("DROP TYPE IF EXISTS leaseclassification CASCADE"))
    test_engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """
    Create a new database session for a test.

    Scope: function - new session per test
    PostgreSQL best practice: Use transactions that rollback after each test
    This ensures test isolation and prevents test data pollution.
    """
    connection = engine.connect()
    transaction = connection.begin()

    # Create session bound to the connection
    TestSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = TestSessionLocal()

    yield session

    # Always rollback per-test changes to keep isolation.
    # TEST_PRESERVE_DB only controls whether the schema is dropped after the session.
    session.close()
    try:
        transaction.rollback()
    except Exception:
        # Transaction may already be inactive if the test triggered a rollback.
        pass
    connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with a test database session.

    This fixture overrides the get_db dependency to use our test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close here, managed by db_session fixture

    async def override_verify_token(
        security_scopes: SecurityScopes,
        token: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    ):
        return {"sub": "test-user", "scope": ""}

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[leases_auth.verify] = override_verify_token
    app.dependency_overrides[schedules_auth.verify] = override_verify_token
    app.dependency_overrides[payments_auth.verify] = override_verify_token

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# Sample data fixtures

@pytest.fixture
def sample_lease_data():
    """Sample lease data for testing"""
    return {
        "lease_name": "Office Space Lease",
        "lessor_name": "ABC Properties",
        "lessee_name": "Tech Startup Inc",
        "commencement_date": "2024-01-01",
        "lease_term_months": 36,
        "periodic_payment": 5000.00,
        "payment_frequency": "monthly",
        "initial_direct_costs": 1000.00,
        "prepaid_rent": 0.00,
        "lease_incentives": 0.00,
        "residual_value": 0.00,
        "incremental_borrowing_rate": 0.05,
        "discount_rate": 0.05,
        "classification": "operating",
        "contract_type": "lease",
        "status": "active"
    }


@pytest.fixture
def sample_lease(db_session: Session, sample_lease_data):
    """Create and return a sample lease in the database"""
    lease = Lease(**sample_lease_data)
    db_session.add(lease)
    db_session.commit()
    db_session.refresh(lease)
    return lease


@pytest.fixture
def sample_finance_lease_data():
    """Sample finance lease data for testing"""
    return {
        "lease_name": "Equipment Lease",
        "lessor_name": "Equipment Leasing Co",
        "lessee_name": "Manufacturing Corp",
        "commencement_date": "2024-01-01",
        "lease_term_months": 60,
        "periodic_payment": 10000.00,
        "payment_frequency": "monthly",
        "initial_direct_costs": 5000.00,
        "prepaid_rent": 10000.00,
        "lease_incentives": 2000.00,
        "residual_value": 50000.00,
        "incremental_borrowing_rate": 0.06,
        "discount_rate": 0.06,
        "classification": "finance",
        "contract_type": "lease",
        "status": "active"
    }


@pytest.fixture
def sample_finance_lease(db_session: Session, sample_finance_lease_data):
    """Create and return a sample finance lease in the database"""
    lease = Lease(**sample_finance_lease_data)
    db_session.add(lease)
    db_session.commit()
    db_session.refresh(lease)
    return lease


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "username": "testuser",
        "password": "securepassword123",
        "name": "Test User",
        "role": "Contract Administrator"
    }


@pytest.fixture
def sample_user(db_session: Session, sample_user_data):
    """Create and return a sample user in the database"""
    user = Users(**sample_user_data)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_journal_entry_data(sample_lease):
    """Sample journal entry data for testing"""
    return {
        "contract_id": str(sample_lease.id),
        "entry_date": "2024-01-01T00:00:00",
        "description": "Initial ROU Asset recognition",
        "debit_account": "Right-of-Use Asset",
        "credit_account": "Lease Liability",
        "amount": 150000.00,
        "reference": "LEASE-001"
    }


@pytest.fixture
def cleanup_database(db_session: Session):
    """
    Cleanup fixture to ensure clean database state.

    PostgreSQL best practice: Clean up in reverse order of foreign key dependencies
    """
    yield

    # Clean up in reverse order of dependencies
    db_session.query(LeaseScheduleEntry).delete()
    db_session.query(ASC842Schedule).delete()
    db_session.query(IFRS16Schedule).delete()
    db_session.query(JournalEntries).delete()
    db_session.query(JournalEntrySetups).delete()
    db_session.query(Payments).delete()
    db_session.query(Documents).delete()
    db_session.query(Lease).delete()
    db_session.query(Users).delete()
    db_session.commit()
