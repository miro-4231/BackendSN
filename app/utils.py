from pwdlib import PasswordHash
from sqlmodel import Session, select, delete
from app.db import engine
from app import model
from datetime import datetime, timezone

password_hasher = PasswordHash.recommended()

def get_password_hash(password):
    return password_hasher.hash(password)

def verify_password(plain_password, hashed_password):
    return password_hasher.verify(plain_password, hashed_password)

def get_db():
    with Session(engine) as session:
        yield session

def cleanup_revoked_tokens():
    """Delete revoked refresh tokens from database"""
    with Session(engine) as session:
        statement = delete(model.RefreshTokens)\
        .where(model.RefreshTokens.is_revoked == True)
        session.exec(statement)
        session.commit()

def cleanup_expired_tokens():
    """Delete expired refresh tokens from database"""
    with Session(engine) as session:
        statement = delete(model.RefreshTokens).where(
            model.RefreshTokens.expires_at < datetime.now(timezone.utc)
        )
        session.exec(statement)
        session.commit()

