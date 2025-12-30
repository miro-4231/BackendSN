from fastapi import FastAPI, status, HTTPException
from contextlib import asynccontextmanager
from sqlmodel import Session, SQLModel, select, desc, update
from typing import List
from app.db import engine
import app.model as model
import app.schemas as schemas
from routers import post_route, auth_route

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    engine.dispose()

app = FastAPI(lifespan=lifespan) 

app.include_router(post_route.router)
app.include_router(auth_route.router)

    
