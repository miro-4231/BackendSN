from fastapi import FastAPI
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import SQLModel
from typing import List
from app.db import engine, initialize_vector_extension
import app.utils as utils
# import app.model as model
# import app.schemas as schemas
from routers import post_route, auth_route, vote_route, comment_route, feed_route

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await initialize_vector_extension(engine)
        await conn.run_sync(SQLModel.metadata.create_all)
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
app.include_router(vote_route.router)
app.include_router(comment_route.router)
app.include_router(feed_route.router)

    
