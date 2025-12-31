from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class Post_in(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
      
class Post_out(Post_in):
    id: int
    created_at: datetime
    
class User_new(BaseModel):
    username: str = Field(max_length=18)
    email: EmailStr = Field(max_length=36)
    password: str = Field(max_length=24)
    
class User_in(BaseModel):
    email: EmailStr = Field(max_length=36)
    password: str = Field(max_length=24)
    
class User_out(BaseModel):
    id: int 
    username: str = Field(max_length=18)
    email: EmailStr = Field(max_length=36)
    created_at: datetime
    
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: EmailStr | None = None