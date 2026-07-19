"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import settings
from .database import Base, engine
from .routers import auth, tasks

# Create tables on startup. For a larger project, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)


def _ensure_column(column: str) -> None:
    """Lightweight migration: add a nullable tasks column to pre-existing SQLite DBs.

    Fresh databases already get the column from create_all above, so the
    ALTER TABLE only runs for old dev databases that predate the field.
    """
    if engine.url.get_backend_name() != "sqlite":
        return
    with engine.begin() as conn:
        columns = [row[1] for row in conn.execute(text("PRAGMA table_info(tasks)"))]
        if columns and column not in columns:
            conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {column} DATETIME"))


_ensure_column("due_date")
_ensure_column("completed_at")

app = FastAPI(title="DevBoard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
