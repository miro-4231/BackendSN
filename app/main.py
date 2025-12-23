from fastapi import FastAPI, status, HTTPException
from contextlib import asynccontextmanager
from sqlmodel import Session, SQLModel, select, desc, update
from typing import List
from app.db import engine
import app.model as model
import app.schemas as schemas

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    engine.dispose()

app = FastAPI(lifespan=lifespan) 

    

@app.get("/posts", response_model=List[schemas.Post_return])
async def root():
    with Session(engine) as session:
        statement = select(model.Posts)
        posts = session.exec(statement).all()
    return posts

@app.get("/posts/latest", response_model=schemas.Post_return)
def get_posts():
    with Session(engine) as session:
        statement = select(model.Posts).order_by(desc(model.Posts.created_at))
        post_latest = session.exec(statement).first()
    return post_latest

@app.get("/posts/{id}", response_model=schemas.Post_return)
def get_post(id:int):
    with Session(engine) as session:
        statement = select(model.Posts).where(model.Posts.id == id)
        post = session.exec(statement).first()

    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return post

@app.post("/posts", status_code=status.HTTP_201_CREATED, response_model=schemas.Post_return)
def create_posts(post:schemas.Post):
    with Session(engine) as session:
        new_post = model.Posts(title=post.title, content=post.content, published=post.published)
        session.add(new_post)
        session.commit()
        session.refresh(new_post)
    return new_post


@app.put("/posts/{id}", status_code=status.HTTP_200_OK, response_model=schemas.Post_return)
def update_post(post:schemas.Post, id:int):
    
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

@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id:int):
    with Session(engine) as session:
        
        statement = select(model.Posts).where(model.Posts.id == id)
        results = session.exec(statement)
        post_del = results.one()
        if not post_del:
            raise HTTPException(status_code=404, detail=f"post with id: {id} not found")
        
        session.delete(post_del)
        session.commit()



