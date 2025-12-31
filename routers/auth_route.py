from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.security import  OAuth2PasswordRequestForm
from sqlmodel import select, update, desc
from datetime import timedelta
from sqlmodel import Session
from app import schemas, model
from typing import List, Annotated
from pydantic import EmailStr
from app.db import engine 
from app import utils
from app import oauth2

ACCESS_TOKEN_EXPIRE_MINUTES = 30


router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=schemas.User_out)
async def new_user(user: schemas.User_new):
    with Session(engine) as session:
        # Check if user already exists
        existing_user = session.exec(select(model.Users).where(model.Users.email == user.email)).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        
        password_hash = utils.get_password_hash(user.password)
        db_user = model.Users(username=user.username, email=user.email, password=password_hash) 
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user 

@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], 
) -> schemas.Token : 
    user = oauth2.authenticate_user(form_data.username, form_data.password)
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = oauth2.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return schemas.Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=schemas.User_out)
async def read_users_me(
    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
):
    return current_user
        
    



