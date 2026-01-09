from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, status, HTTPException, Depends
from datetime import datetime, timedelta, timezone
from sqlmodel import select, update, desc
from sqlmodel import Session
from typing import List, Annotated
from pydantic import EmailStr
from app import schemas, model
from app.db import engine 
from app import utils

import jwt
from jwt.exceptions import InvalidTokenError
import uuid


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "f49f6c1d244648d6e88b2be59e165125d3a4099ac580f94dccecb2fd8c69c46b"
ALGORITHM = "HS256"



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token", refreshUrl="auth/refresh")


def get_user_by_id(id: int, session: Session) -> model.Users:
    statement = select(model.Users).where(model.Users.id == id)
    user = session.exec(statement).first()
    return user

def get_user_by_username(username: str, session: Session) -> model.Users:
    statement = select(model.Users).where(model.Users.username == username)
    user = session.exec(statement).first()
    return user

def check_refresh_token(token: str, jti: str, session: Session) -> model.RefreshTokens: 
    statement = select(model.RefreshTokens)\
    .where(model.RefreshTokens.jti == jti)
    
    refresh_token = session.exec(statement).first()
    if refresh_token is None:
        return None
    elif refresh_token.is_revoked:
        return False
    elif refresh_token and utils.verify_password(token, refresh_token.token_hash):
        return refresh_token
    return None


def authenticate_user(id: int|str, password: str, session: Session): 
    if isinstance(id, str):
        user = get_user_by_username(id, session)
    elif isinstance(id, int):
        user = get_user_by_id(id, session)
    else:
        return False 
    if not user:
        return False 
    if not utils.verify_password(password, user.password): 
        return False
    return user 

def create_access_token(data:dict, expires_delta:timedelta | None = None):
    to_encode = data.copy() 
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta 
    else: 
        expire = datetime.now(timezone.utc) + timedelta(days=7) 
    to_encode.update({"exp": expire, "typ": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=30)
    to_encode.update({"exp": expire, "typ": "refresh", "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    print(encoded_jwt)
    return encoded_jwt, jti

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: Annotated[Session, Depends(utils.get_db)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not valid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )    
    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id = int(payload.get("sub"))
        type = payload.get("typ")
        if type != "access": 
            raise credentials_exception
        if id is None:
            raise credentials_exception
    except InvalidTokenError :
        raise credentials_exception
    user = get_user_by_id(id, session)
    if user is None:
        raise credentials_exception 
    return user

async def verify_refresh_token(token: Annotated[str, Depends(oauth2_scheme)], session: Annotated[Session, Depends(utils.get_db)]) -> int:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )    
    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id = payload.get("sub")
        jti = payload.get("jti")
        type_tkn = payload.get("typ")
        if type_tkn != "refresh": 
            raise credentials_exception
        if id is None or jti is None:
            raise credentials_exception
    except InvalidTokenError as error:
        raise credentials_exception
    refresh_token = check_refresh_token(token, jti, session)
    if not refresh_token: 
        session.delete(select(model.RefreshTokens).where(model.RefreshTokens.user_id == int(id)))
        raise credentials_exception
    if refresh_token is None or refresh_token.user_id != int(id):
        raise credentials_exception 
    
    # Revoke old refresh token for rotation
    db_token = session.exec(select(model.RefreshTokens).where(model.RefreshTokens.jti == jti)).first()
    if db_token:
        db_token.is_revoked = True
        session.add(db_token)
        session.commit()
    
    return refresh_token.user_id





