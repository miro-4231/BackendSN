from fastapi import FastAPI, Response, status, HTTPException
from fastapi.params import Body
from pydantic import BaseModel
from typing import Optional
from random import randint
import psycopg
from psycopg import errors
from psycopg.rows import dict_row

app = FastAPI() 

class Post(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
    rating: Optional[int] = None
    
    
try:
    conn = psycopg.connect(host = 'localhost', dbname= 'fastapi',
                           user = 'postgres', password = '2003', connect_timeout=30, row_factory=dict_row)
    cursor = conn.cursor()
    print("Database connection was succefull!!")
except Exception as error:
    print("Connection to database Failed !!")
    print("Error: ", error)
    
    

my_posts = [{"title":"title of post 1", "content":"content of post 1", "id":1}, 
            {"title":"fav food", "content":"I like pizza", "id":2}]

def find_post(id:int):
    for post in my_posts:
        if post["id"] == id: 
            return post


@app.get("/posts")
async def root():
    cursor.execute("""SELECT * FROM posts""")
    data = cursor.fetchall()
    return {"data" : data}

@app.get("/posts/latest")
def get_posts():
    cursor.execute(  """SELECT * FROM posts 
                        WHERE published = true 
                        ORDER BY created_at DESC 
                        LIMIT 1;""")
    data = cursor.fetchall()
    return {"data" : data}

@app.get("/posts/{id}")
def get_post(id:int):
    cursor.execute(  """SELECT * FROM posts 
                        WHERE id = %s 
                        LIMIT 1;""", [id])
    data = cursor.fetchall()
    if not data: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'post with id: {id} not found.')
    return {"data" : data}

@app.post("/posts", status_code=status.HTTP_201_CREATED)
def create_posts(post:Post):
    try:
        cursor.execute( """
                    INSERT INTO posts (title, content, published)
                    VALUES (%s, %s, %s) RETURNING *;
                    """, [post.title, post.content, post.published])
        new_post = cursor.fetchone()
        conn.commit()
        return new_post
        
    except errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Post already exists")
        
    except errors.NotNullViolation as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Missing required field")
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.put("/posts/{id}", status_code=status.HTTP_200_OK)
def update_post(post:Post, id:int):
    try:
        cursor.execute("""
            UPDATE posts 
            SET title = %s, content = %s, published = %s
            WHERE id = %s
            RETURNING *;
        """, (post.title, post.content, post.published, id))
        
        updated_post = cursor.fetchone()
        
        if updated_post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        
        conn.commit()
        return updated_post
        
    except HTTPException:
        raise  # Let our 404 pass through
        
    except Exception as e:
        conn.rollback()
        # Log the real error for debugging
        import logging
        logging.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update post")

@app.delete("/posts/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(id:int):
    try:
        cursor.execute("""
            DELETE FROM posts
            WHERE id = %s
            RETURNING *;
        """, (id,))
        
        updated_post = cursor.fetchone()
        
        if updated_post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        
        conn.commit()
        return updated_post
        
    except HTTPException:
        raise  # Let our 404 pass through
        
    except Exception as e:
        conn.rollback()
        # Log the real error for debugging
        import logging
        logging.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to update post")


