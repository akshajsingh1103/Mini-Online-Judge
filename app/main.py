from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.routes import auth, problems, submissions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler (replaces deprecated on_event)."""
    # Startup: nothing extra needed — Alembic handles DB migrations.
    yield
    # Shutdown: nothing to clean up at application level.


app = FastAPI(
    title="Mini Online Judge",
    version="1.0.0",
    description=(
        "A scaled-down online judge system supporting code submission, "
        "automated judging (Python & C++), and verdict generation — "
        "built with FastAPI, PostgreSQL, and SQLAlchemy."
    ),
    lifespan=lifespan,
)

# --- Routers ---
app.include_router(auth.router)
app.include_router(problems.router)
app.include_router(submissions.router)


# --- Health check ---
@app.get("/", tags=["Health"], summary="Service health check")
def health_check() -> dict:
    return {"status": "ok", "service": "Mini Online Judge"}
