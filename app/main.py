from fastapi import FastAPI, Response, status, HTTPException
from contextlib import asynccontextmanager
from fastapi.params import Body
from pydantic import BaseModel
from typing import Optional
from sqlmodel import Session, select, desc, update
from app.db import *

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield
    engine.dispose()

app = FastAPI(lifespan=lifespan) 

class Post_api(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
    

@app.get("/posts")
async def root():
    with Session(engine) as session:
        statement = select(Posts)
        posts = session.exec(statement).all()
    return {"data" : posts}

@app.get("/posts/latest")
def get_posts():
    with Session(engine) as session:
        statement = select(Posts).order_by(desc(Posts.created_at))
        post_latest = session.exec(statement).first()
    return {"data" : post_latest}

@app.get("/posts/{id}")
def get_post(id:int):
    with Session(engine) as session:
        statement = select(Posts).where(Posts.id == id)
        post = session.exec(statement).first()

    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return {"data" : post}

@app.post("/posts", status_code=status.HTTP_201_CREATED)
def create_posts(post:Post_api):
    with Session(engine) as session:
        new_post = Posts(title=post.title, content=post.content, published=post.published)
        session.add(new_post)
        session.commit()
        session.refresh(new_post)
    return {"data" : new_post}


@app.put("/posts/{id}", status_code=status.HTTP_200_OK)
def update_post(post:Post_api, id:int):
    
    with Session(engine) as session:
        target_post = session.get(Posts, id)
        if not target_post:
            raise HTTPException(status_code=404, detail=f"post with id: {id} not found")
        statement = (
            update(Posts)
            .where(Posts.id == id)
            .values(title=post.title, content=post.content, published=post.published)
        )
        session.exec(statement)
        session.commit()  
        
        session.refresh(target_post)
    
    return target_post

@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id:int):
    with Session(engine) as session:
        
        statement = select(Posts).where(Posts.id == id)
        results = session.exec(statement)
        post_del = results.one()
        if not post_del:
            raise HTTPException(status_code=404, detail=f"post with id: {id} not found")
        
        session.delete(post_del)
        session.commit()



