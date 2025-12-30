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


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "f49f6c1d244648d6e88b2be59e165125d3a4099ac580f94dccecb2fd8c69c46b"
ALGORITHM = "HS256"



oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_user(email:EmailStr) -> model.Users:
    with Session(engine) as session: 
        statement = select(model.Users).where(model.Users.email == email)
        user = session.exec(statement).first()
    return user


def authenticate_user(email: EmailStr, password:str):  
    user = get_user(email)
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
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, 
        detail="Could not valid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try: 
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(email)
    if user is None:
        raise credentials_exception 
    return user


        


