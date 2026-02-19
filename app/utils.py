from pwdlib import PasswordHash
from sqlmodel import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from numpy import array
from app.db import async_session_factory
from datetime import datetime, timezone
from app import model

password_hasher = PasswordHash.recommended()

LEARNING_RATE = 0.05

def get_password_hash(password):
    return password_hasher.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hasher.verify(plain_password, hashed_password)

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

async def cleanup_revoked_tokens():
    """Delete revoked refresh tokens from database"""
    async with async_session_factory() as session:  # fix: was `with` (sync), must be `async with`
        async with session.begin():
            statement = delete(model.RefreshTokens)\
            .where(model.RefreshTokens.is_revoked == True)
            await session.execute(statement)

async def cleanup_expired_tokens():
    """Delete expired refresh tokens from database"""
    async with async_session_factory() as session:  # fix: was `with` (sync), must be `async with`
        async with session.begin():
            statement = delete(model.RefreshTokens).where(
                model.RefreshTokens.expires_at < datetime.now(timezone.utc)
            )
            await session.execute(statement)

async def update_user_embedding(user_id: int, session: AsyncSession, embedding: list):
    # Fetch the user's current embedding
    result = await session.execute(
        select(model.Users.embedding).where(model.Users.id == user_id)
    )
    current_embedding = result.scalar_one_or_none()

    # Compute EMA in Python — pgvector has no scalar*vector operator
    new_emb = array(embedding)
    if current_embedding is not None:
        new_emb = (1 - LEARNING_RATE) * array(current_embedding) + LEARNING_RATE * new_emb

    # Serialize to pgvector string format and write back
    emb_str = "[" + ",".join(str(x) for x in new_emb.tolist()) + "]"
    await session.execute(
        text("UPDATE users SET embedding = CAST(:emb AS vector(384)) WHERE id = :user_id"),
        {"emb": emb_str, "user_id": user_id}
    )
    await session.commit()

async def run_background_update(user_id: int, embedding: list):
    """
    Runs after the user has received their response.
    Creates its own database session to avoid holding the request session open.
    """
    async with async_session_factory() as session:
        await update_user_embedding(user_id, session, embedding)
