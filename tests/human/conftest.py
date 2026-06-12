import os
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.human.database import Base, get_db
from app.human.models.candidate import Candidate
from app.human.models.application import Application
from app.human.models.recruitment import Recruitment
from app.human.models.talent import Talent, TalentStatus
from app.human.routers import candidates, ingest, pipeline, pool, queue, recruitments, applications


@pytest.fixture
def db() -> Generator[Session, None, None]:
    """Create a temporary SQLite database for testing."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import app.human.models  # noqa: F401
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        os.unlink(db_path)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ingest.router)
    app.include_router(queue.router)
    app.include_router(pipeline.router)
    app.include_router(pool.router)
    app.include_router(recruitments.router)
    app.include_router(candidates.router)
    app.include_router(applications.router)
    return app


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with all HR routers using temp DB."""
    app = _build_app()
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c


@pytest.fixture
def seeded_db(db: Session) -> Session:
    """Pre-seed DB with a recruitment, two candidates, two applications, two talents."""
    r = Recruitment()
    db.add(r)
    db.flush()

    c1 = Candidate(email="test1@test.com", real_name="测试一号")
    c2 = Candidate(email="test2@test.com", real_name="测试二号")
    db.add(c1)
    db.add(c2)
    db.flush()

    a1 = Application(
        candidate_id=c1.id, recruitment_id=r.id,
        status=TalentStatus.INTERVIEW, source="test_seed",
    )
    a2 = Application(
        candidate_id=c2.id, recruitment_id=r.id,
        status=TalentStatus.CLOSED, source="test_seed",
        pooled_at=datetime.now(timezone.utc),
        deactivated_at=datetime.now(timezone.utc),
    )
    db.add(a1)
    db.add(a2)
    db.flush()

    t1 = Talent(recruitment_id=r.id, email="test1@test.com", real_name="测试一号", status=TalentStatus.INTERVIEW)
    t2 = Talent(recruitment_id=r.id, email="test2@test.com", real_name="测试二号", status=TalentStatus.CLOSED)
    db.add(t1)
    db.add(t2)
    db.commit()
    return db


@pytest.fixture
def seeded_client(seeded_db: Session) -> Generator[TestClient, None, None]:
    """Client with pre-seeded data (recruitment, candidates, applications, talents)."""
    app = _build_app()
    app.dependency_overrides[get_db] = lambda: seeded_db
    with TestClient(app) as c:
        yield c
