import atexit
import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent

TEST_DB_CONTAINER = f"releasegate-test-db-{uuid.uuid4().hex[:8]}"
TEST_DB_USER = "releasegate"
TEST_DB_PASSWORD = "releasegate"
TEST_DB_NAME = "releasegate"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


TEST_DB_PORT = _free_port()
TEST_DATABASE_URL = (
    f"postgresql+psycopg2://{TEST_DB_USER}:{TEST_DB_PASSWORD}"
    f"@127.0.0.1:{TEST_DB_PORT}/{TEST_DB_NAME}"
)


def _docker_binary() -> str:
    for candidate in ("docker", "/usr/local/bin/docker", "/opt/homebrew/bin/docker"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError(
        "Docker is required to run the backend test suite (integration tests run "
        "against a dockerized PostgreSQL, never SQLite)."
    )


DOCKER = _docker_binary()


def _start_test_database() -> None:
    result = subprocess.run(
        [
            DOCKER,
            "run",
            "-d",
            "--rm",
            "--name",
            TEST_DB_CONTAINER,
            "-p",
            f"{TEST_DB_PORT}:5432",
            "-e",
            f"POSTGRES_USER={TEST_DB_USER}",
            "-e",
            f"POSTGRES_PASSWORD={TEST_DB_PASSWORD}",
            "-e",
            f"POSTGRES_DB={TEST_DB_NAME}",
            "postgres:15",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start dockerized test Postgres: {result.stderr.strip()}")


def _wait_until_ready(timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        probe = subprocess.run(
            [DOCKER, "exec", TEST_DB_CONTAINER, "pg_isready", "-U", TEST_DB_USER],
            capture_output=True,
            check=False,
        )
        if probe.returncode == 0:
            return
        time.sleep(0.5)
    raise RuntimeError("Dockerized test Postgres did not become ready in time.")


def _stop_test_database() -> None:
    subprocess.run([DOCKER, "rm", "-f", TEST_DB_CONTAINER], capture_output=True, check=False)


_start_test_database()
atexit.register(_stop_test_database)

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = "test-secret-key"


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    _wait_until_ready()
    from alembic.config import Config

    from alembic import command

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def clean_tables() -> None:
    yield
    from sqlalchemy import text

    from app.database import engine

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE audit_events, approvals, change_requests, users "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def db():
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def make_user(db):
    def _make(role, email: str | None = None):
        from app.models import User
        from app.security import hash_password

        email = email or f"{role.value.lower()}-{uuid.uuid4().hex[:8]}@test.dev"
        user = User(
            email=email,
            full_name=f"{role.value.title()} User",
            role=role,
            hashed_password=hash_password("password123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def make_token():
    from app.security import create_access_token

    def _make(user) -> str:
        return create_access_token(str(user.id))

    return _make


@pytest.fixture
def auth_headers(make_token):
    def _headers(user) -> dict[str, str]:
        return {"Authorization": f"Bearer {make_token(user)}"}

    return _headers


@pytest.fixture
def make_change_request(db):
    from datetime import UTC, datetime, timedelta

    from app.enums import ChangeStage, RiskLevel
    from app.models import AuditEvent, ChangeRequest

    counter = iter(range(5000, 9999))

    def _make(
        requester,
        *,
        stage: ChangeStage = ChangeStage.DRAFT,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        title: str = "Test change",
        ticket_key: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        audit_events: list[AuditEvent] | None = None,
    ) -> ChangeRequest:
        now = datetime.now(UTC)
        created_at = created_at or now - timedelta(days=1)
        updated_at = updated_at or created_at
        change_request = ChangeRequest(
            ticket_key=ticket_key or f"ECR-{next(counter)}",
            title=title,
            description="Integration test change request.",
            vehicle_program="TestProgram",
            subsystem="TestSubsystem",
            risk_level=risk_level,
            current_stage=stage,
            requester_id=requester.id,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(change_request)
        db.flush()

        if audit_events is not None:
            for event in audit_events:
                event.change_request_id = change_request.id
            db.add_all(audit_events)
        else:
            timeline: list[tuple[ChangeStage | None, ChangeStage, str]] = [
                (None, ChangeStage.DRAFT, "CREATED"),
                (ChangeStage.DRAFT, ChangeStage.SUBMITTED, "SUBMITTED"),
                (
                    ChangeStage.SUBMITTED,
                    ChangeStage.ENGINEERING_REVIEW,
                    "MOVED_TO_ENGINEERING_REVIEW",
                ),
                (
                    ChangeStage.ENGINEERING_REVIEW,
                    ChangeStage.MANUFACTURING_REVIEW,
                    "MOVED_TO_MANUFACTURING_REVIEW",
                ),
                (ChangeStage.MANUFACTURING_REVIEW, ChangeStage.APPROVED, "APPROVED"),
                (ChangeStage.MANUFACTURING_REVIEW, ChangeStage.REJECTED, "REJECTED"),
            ]
            stage_index = [to_stage for _, to_stage, _ in timeline].index(stage)
            events = [
                AuditEvent(
                    change_request_id=change_request.id,
                    actor_id=requester.id,
                    from_stage=from_stage,
                    to_stage=to_stage,
                    action=action,
                    meta={},
                    created_at=created_at + timedelta(hours=index),
                )
                for index, (from_stage, to_stage, action) in enumerate(timeline[: stage_index + 1])
            ]
            db.add_all(events)
        db.commit()
        return change_request

    return _make
