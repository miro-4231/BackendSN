from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Post_in(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
    
    
class Post_out(Post_in):
    id: int
    created_at: datetime
    
class User_in(BaseModel):
    email: EmailStr 
    password: str 
    
class User_out(BaseModel):
    id: int 
    email: EmailStr
    created_at: datetime