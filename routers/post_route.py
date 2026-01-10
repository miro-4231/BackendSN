from fastapi import APIRouter, status, HTTPException, Query, Depends
from sqlmodel import select, update, desc
from sqlmodel import Session
from sqlalchemy.orm import joinedload
from app import schemas, model, oauth2, utils
from typing import List, Annotated


router = APIRouter(prefix="/posts", tags=["Posts"])


@router.get("/", response_model=List[schemas.Post_out])
async def root(
    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], 
    session: Annotated[Session, Depends(utils.get_db)],
    limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    search: str = Query(default="", description="Search term")):
    
    statement = select(model.Posts).filter(model.Posts.content.like("%" + search + "%"))\
        .options(joinedload(model.Posts.author)).offset(offset).limit(limit)
    posts = session.exec(statement).all()
    return posts

@router.get("/latest", response_model=schemas.Post_out)
async def get_latest_post(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    statement = select(model.Posts).order_by(desc(model.Posts.created_at))
    post_latest = session.exec(statement).first()
    return post_latest

@router.get("/me", response_model=List[schemas.Post_out])
async def get_me_post(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)],
                    limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
                    offset: int = Query(default=0, ge=0, description="Number of items to skip")):
    
    statement = select(model.Posts).where(model.Posts.author_id == current_user.id).offset(offset).limit(limit)
    posts = session.exec(statement).all()
    return posts

@router.get("/{id}", response_model=schemas.Post_out)
async def get_post_by_id(id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    statement = select(model.Posts).where(model.Posts.id == id)
    post = session.exec(statement).first()

    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return post

@router.get("/user/{user_id}", response_model=List[schemas.Post_out])
async def get_user_posts(user_id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[Session, Depends(utils.get_db)],
                        limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
                        offset: int = Query(default=0, ge=0, description="Number of items to skip")):
    # Check if user already exists
    existing_user = session.exec(select(model.Users).where(model.Users.id == user_id)).first()
    if existing_user:
        statement = select(model.Posts).where(model.Posts.author_id == user_id)\
            .options(joinedload(model.Posts.author)).offset(offset).limit(limit)
        posts = session.exec(statement).all()
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f'User with id:{user_id} not found')

    if not posts: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'User with id:{user_id} hasn\'t posted anything yet')
    return posts



@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post_out)
async def create_posts(post: schemas.Post_in, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    new_post = model.Posts(title=post.title, content=post.content, author_id=current_user.id, published=post.published)
    session.add(new_post)
    session.commit()
    session.refresh(new_post)
    return new_post


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Post_out)
async def update_post(post: schemas.Post_in, id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    target_post = session.get(model.Posts, id)
    if not target_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {id} not found")
    if current_user.id != target_post.author_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to perform requested action")
    
    statement = (
        update(model.Posts)
        .where(model.Posts.id == id)
        .values(title=post.title,
                content=post.content,
                published=post.published)
    )
    session.exec(statement)
    session.commit()  
    
    session.refresh(target_post)
    
    return target_post

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(id: int, current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)], session: Annotated[Session, Depends(utils.get_db)]):
    statement = select(model.Posts).where(model.Posts.id == id)
    post_del = session.exec(statement).first()
    
    if not post_del:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"post with id: {id} not found")
    if current_user.id != post_del.author_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authorized to perform requested action")
    
    session.delete(post_del)
    session.commit()
