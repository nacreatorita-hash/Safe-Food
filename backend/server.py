import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Supabase/Postgres connection
from lib.db import check_database, close, ensure_indexes
from repositories.status import insert_status, list_status


# Startup runs before the yield, shutdown after it. Add your own setup/teardown here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())  # background: a big index build must not block boot
    yield
    app.state.index_task.cancel()
    await close()


# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Hello World"}


@api_router.get("/health")
async def health():
    """Liveness: succeeds without touching MongoDB or external sources."""
    return {"status": "ok", "service": "food-alert-api"}


@api_router.get("/ready")
async def readiness():
    """Readiness: bounded Supabase/Postgres probe, never an unbounded request."""
    try:
        timeout = max(0.5, float(os.environ.get("READINESS_TIMEOUT_SECONDS", "2")))
    except ValueError:
        timeout = 2.0
    try:
        await asyncio.wait_for(check_database(), timeout=timeout)
    except Exception as exc:
        logger.info("readiness non disponibile: %s", exc)
        raise HTTPException(status_code=503, detail={"status": "not_ready", "database": "unavailable"}) from exc
    return {"status": "ready", "database": "ok"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    await insert_status(status_obj.model_dump())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await list_status()
    return [StatusCheck(**status_check) for status_check in status_checks]

from routers import admin, auth, fao, notifications, pantry, recalls, sources  # noqa: E402

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(recalls.router, tags=["recalls"])
api_router.include_router(pantry.router, tags=["pantry"])
api_router.include_router(fao.router, tags=["fao"])
api_router.include_router(notifications.router, tags=["notifications"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(sources.router, tags=["sources"])

# Include the router in the main app
app.include_router(api_router)

cors_origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",") if origin.strip()]
cors_wildcard = cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_credentials=not cors_wildcard,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
