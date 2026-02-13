from app.model import * 
from sqlmodel import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL") 

# Create engine
engine = create_async_engine(DATABASE_URL, echo=True, pool_size=20, max_overflow=10)

async def initialize_vector_extension(engine):
    async with engine.begin() as conn:
        # We use .begin() to ensure it's wrapped in a transaction
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print("✅ pgvector extension is ready")


# expire_on_commit=False is CRITICAL for Async
async_session_factory = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)