from fastapi import APIRouter, status, HTTPException
from sqlmodel import select, update, desc
from sqlmodel import Session
from app import schemas, model
from typing import List 
from app.db import engine 


router = APIRouter(prefix="/posts", tags=["Posts"])




@router.get("/", response_model=List[schemas.Post_out])
async def root():
    with Session(engine) as session:
        statement = select(model.Posts)
        posts = session.exec(statement).all()
    return posts

@router.get("/latest", response_model=schemas.Post_out)
def get_posts():
    with Session(engine) as session:
        statement = select(model.Posts).order_by(desc(model.Posts.created_at))
        post_latest = session.exec(statement).first()
    return post_latest

@router.get("/{id}", response_model=schemas.Post_out)
def get_post(id:int):
    with Session(engine) as session:
        statement = select(model.Posts).where(model.Posts.id == id)
        post = session.exec(statement).first()

    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return post

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.Post_out)
def create_posts(post:schemas.Post_in):
    with Session(engine) as session:
        new_post = model.Posts(title=post.title, content=post.content, published=post.published)
        session.add(new_post)
        session.commit()
        session.refresh(new_post)
    return new_post


@router.put("/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Post_out)
def update_post(post:schemas.Post_in, id:int):
    
    with Session(engine) as session:
        target_post = session.get(model.Posts, id)
        if not target_post:
            raise HTTPException(status_code=404, detail=f"post with id: {id} not found")
        statement = (
            update(model.Posts)
            .where(model.Posts.id == id)
            .values(title=post.title, content=post.content, published=post.published)
        )
        session.exec(statement)
        session.commit()  
        
        session.refresh(target_post)
    
    return target_post

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id:int):
    with Session(engine) as session:
        
        statement = select(model.Posts).where(model.Posts.id == id)
        results = session.exec(statement)
        post_del = results.one()
        if not post_del:
            raise HTTPException(status_code=404, detail=f"post with id: {id} not found")
        
        session.delete(post_del)
        session.commit()