import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.human.database import Base, engine, init_db
from app.human.routers import candidates, ingest, pipeline, pool, queue, recruitments, applications


def seed_data_if_empty():
    """Check if DB is empty and seed demo data if so."""
    from sqlalchemy.orm import Session
    from app.human.database import SessionLocal
    db = SessionLocal()
    try:
        from app.human.models.recruitment import Recruitment
        exists = db.query(Recruitment).first()
        if not exists:
            from app.human.seed import seed_data
            seed_data(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_data_if_empty()
    yield


app = FastAPI(title="qtadmin API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(queue.router)
app.include_router(pipeline.router)
app.include_router(pool.router)
app.include_router(recruitments.router)
app.include_router(candidates.router)
app.include_router(applications.router)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
