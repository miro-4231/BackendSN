from fastapi import APIRouter, status, HTTPException, Query, Depends
from sqlmodel import select, update, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app import schemas, model, oauth2, utils
from typing import List, Annotated


router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=List[schemas.Post_out])
async def root(
    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], 
    session: Annotated[AsyncSession, Depends(utils.get_db)],
    limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    search: str = Query(default="", description="Search term")):
    
    statement = select(model.Posts).filter(or_(model.Posts.content.like("%" + search + "%"), model.Posts.title.like("%" + search + "%")))\
        .options(joinedload(model.Posts.author)).offset(offset).limit(limit)
    result = await session.execute(statement)
    posts = result.scalars().all()
    return posts

@router.get("/latest", response_model=schemas.Post_out)
async def get_latest_post(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[AsyncSession, Depends(utils.get_db)]):
    statement = select(model.Posts).order_by(desc(model.Posts.created_at))
    post_latest = await session.execute(statement)
    return post_latest.scalar_one_or_none()

@router.get("/me", response_model=List[schemas.Post_out])
async def get_me_post(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[AsyncSession, Depends(utils.get_db)],
                    limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
                    offset: int = Query(default=0, ge=0, description="Number of items to skip")):
    
    statement = select(model.Posts).where(model.Posts.author_id == current_user.id).offset(offset).limit(limit)
    posts = await session.execute(statement)
    return posts.scalars().all()

@router.get("/{id}", response_model=schemas.Post_out)
async def get_post_by_id(id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[AsyncSession, Depends(utils.get_db)]):
    statement = select(model.Posts).where(model.Posts.id == id)
    post = await session.execute(statement)
    post = post.scalar_one_or_none()

    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return post

@router.get("/user/{user_id}", response_model=List[schemas.Post_out])
async def get_user_posts(user_id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[AsyncSession, Depends(utils.get_db)],
                        limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
                        offset: int = Query(default=0, ge=0, description="Number of items to skip")):
    # Check if user already exists
    existing_user = await session.execute(select(model.Users).where(model.Users.id == user_id))
    existing_user = existing_user.scalar_one_or_none()
    if existing_user:
        statement = select(model.Posts).where(model.Posts.author_id == user_id)\
            .options(joinedload(model.Posts.author)).offset(offset).limit(limit)
        posts = await session.execute(statement)
        posts = posts.scalars().all()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id:{user_id} not found')

    if not posts: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'User with id:{user_id} hasn\'t posted anything yet')
    return posts



@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post_out)
async def create_posts(post: schemas.Post_in, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[AsyncSession, Depends(utils.get_db)]):
    new_post = model.Posts(title=post.title, content=post.content, author_id=current_user.id, published=post.published)
    session.add(new_post)
    await session.commit()
    await session.refresh(new_post)
    return new_post


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Post_out)
async def update_post(post: schemas.Post_in, id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    target_post = await session.get(model.Posts, id)
    if not target_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {id} not found")
    if current_user.id != target_post.author_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to perform requested action")
    
    post_data = post.model_dump(exclude_unset=True) # Get only the fields provided
    for key, value in post_data.items():
        setattr(target_post, key, value)

    # 3. Commit the changes
    await session.commit()
    
    # 4. Refresh to ensure we have the latest (e.g., if there are DB triggers or default timestamps)
    await session.refresh(target_post)
    
    return target_post

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[AsyncSession, Depends(utils.get_db)]):
    
    post_del = await session.get(model.Posts, id)
    
    if not post_del:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {id} not found")
    if current_user.id != post_del.author_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to perform requested action")
    
    await session.delete(post_del)
    await session.commit()
