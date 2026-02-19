from fastapi import APIRouter, status, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import select 
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta, timezone
from app import schemas, model, utils, oauth2
from typing import Annotated

ACCESS_TOKEN_EXPIRE_MIN = 30
REFRESH_TOKEN_EXPIRE_DAY = 7


router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=schemas.User_out_min)
async def new_user(user: schemas.User_new, session: Annotated[AsyncSession, Depends(utils.get_db)]):
    # Check if user already exists
    existing_user = await session.execute(select(model.Users).where(model.Users.username == user.username))
    existing_user = existing_user.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    password_hash = utils.get_password_hash(user.password)
    db_user = model.Users(username=user.username, email=user.email, password=password_hash) 
    session.add(db_user)
    await session.commit()
    await session.refresh(db_user)
    return db_user 

@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(utils.get_db)]
) -> schemas.Token : 
    user = await oauth2.authenticate_user(form_data.username, form_data.password, session)
    if not user: 
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    access_token = oauth2.create_access_token(
        data={"sub": str(user.id), "typ": "access"}, expires_delta=access_token_expires
    )
    
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAY)
    refresh_token, jti = oauth2.create_refresh_token(
        data={"sub": str(user.id)}, expires_delta=refresh_token_expires
    )
    
    refresh_token_db = model.RefreshTokens(user_id=user.id, token_hash=utils.get_password_hash(refresh_token),
                                           jti=jti, expires_at=datetime.now(timezone.utc)+refresh_token_expires, is_revoked=False)
    session.add(refresh_token_db)
    await session.commit()
    return schemas.Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@router.post("/refresh")
async def refresh(
    user_id: Annotated[int, Depends(oauth2.verify_refresh_token)],
    session: Annotated[AsyncSession, Depends(utils.get_db)]
) -> schemas.Token : 
    print("jaja")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MIN)
    access_token = oauth2.create_access_token(
        data={"sub": str(user_id)}, expires_delta=access_token_expires
    )
    
    # Issue new refresh token for rotation
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAY)
    refresh_token, jti = oauth2.create_refresh_token(
        data={"sub": str(user_id)}, expires_delta=refresh_token_expires
    )
    
    refresh_token_db = model.RefreshTokens(user_id=user_id, token_hash=utils.get_password_hash(refresh_token),
                                           jti=jti, expires_at=datetime.now(timezone.utc)+refresh_token_expires, is_revoked=False)
    session.add(refresh_token_db)
    await session.commit()
    
    return schemas.Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

@router.get("/me", response_model=schemas.User_out_min)
async def read_users_me(
    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
):
    return current_user

@router.delete("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    token: Annotated[str, Depends(oauth2.oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(utils.get_db)]
):
    try:
        print(token)
        payload = oauth2.jwt.decode(token, oauth2.SECRET_KEY, algorithms=[oauth2.ALGORITHM])
        jti = payload.get("jti")
        token_type = payload.get("typ")
        if jti is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except oauth2.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    statement = select(model.RefreshTokens).where(model.RefreshTokens.jti == jti)
    refresh_token = await session.execute(statement)
    refresh_token = refresh_token.scalar_one_or_none()
    
    if refresh_token:
        await session.delete(refresh_token)
        await session.commit()





