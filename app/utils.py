from pwdlib import PasswordHash
from sqlmodel import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, case
from app.db import async_session_factory
from datetime import datetime, timezone
from app import model
from app.encoder import encode_text
from numpy import array

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
    with async_session_factory() as session:
        async with session.begin():
            statement = delete(model.RefreshTokens)\
            .where(model.RefreshTokens.is_revoked == True)
            await session.execute(statement)

async def cleanup_expired_tokens():
    """Delete expired refresh tokens from database"""
    with async_session_factory() as session:
        async with session.begin():
            statement = delete(model.RefreshTokens).where(
                model.RefreshTokens.expires_at < datetime.now(timezone.utc)
            )
            await session.execute(statement)

async def update_user_embedding(user_id: int, session: AsyncSession, content: str):
    new_vector = encode_text(content) 
    stmt = (
        update(model.User)
        .where(model.User.id == user_id)
        .values(
            embedding = case(
                (model.User.embedding == None, new_vector),
                else_ = (1 - LEARNING_RATE) * model.User.embedding + LEARNING_RATE * new_vector
            )
        )
    )
    
    await session.execute(stmt)
    await session.commit() # Save the changes
    

