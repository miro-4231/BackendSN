from fastapi import FastAPI, Response, status, HTTPException
from fastapi.params import Body
from pydantic import BaseModel
from typing import Optional
from random import randint

app = FastAPI() 

class Post(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
    rating: Optional[int] = None

my_posts = [{"title":"title of post 1", "content":"content of post 1", "id":1}, 
            {"title":"fav food", "content":"I like pizza", "id":2}]

def find_post(id:int):
    for post in my_posts:
        if post["id"] == id: 
            return post


@app.get("/posts")
async def root():
    return {"data" : my_posts}

@app.get("/posts/latest")
def get_posts():
    return {"data" : my_posts[-1]}

@app.get("/posts/{id}")
def get_posts(id:int):
    post = find_post(id)
    if not post: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return {"data" : post}

@app.post("/posts", status_code=status.HTTP_201_CREATED)
def create_posts(post:Post):
    post_dict = post.dict()
    post_dict["id"] = randint(0, 10**5)
    my_posts.append(post_dict)
    return {"data": post_dict}

@app.put("/posts/{id}", status_code=status.HTTP_200_OK)
def update_post(post:Post, id:int):
    post_to_update = find_post(id)
    if post_to_update :
        for key, val in post.dict().items() :
            post_to_update[key] = val
        return Response(status_code=status.HTTP_200_OK)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')

@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id:int):
    post_to_delete = find_post(id) 
    if post_to_delete:
        my_posts.remove(post_to_delete)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')


