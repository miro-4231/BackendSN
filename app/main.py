from fastapi import FastAPI, status, HTTPException
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, SQLModel, select, desc, update
from typing import List
from app.db import engine
import app.utils as utils
# import app.model as model
# import app.schemas as schemas
from routers import post_route, auth_route

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    # Startup
    scheduler.add_job(utils.cleanup_revoked_tokens, "interval", hours=24, id="cleanup_revoked")
    scheduler.add_job(utils.cleanup_expired_tokens, "interval", hours=24, id="cleanup_expired")
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()
    engine.dispose()

app = FastAPI(lifespan=lifespan)

app.include_router(post_route.router)
app.include_router(auth_route.router)

    
