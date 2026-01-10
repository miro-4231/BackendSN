from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

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

class Post_in(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
      
class Post_out(Post_in):
    id: int
    author_id: int
    author: User_out
    votes: int
    created_at: datetime
    
class VoteCreate(BaseModel):
    direction: int = Field(..., description="1 for Up, -1 for Down")
    is_super: bool = False

    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: int) -> int:
        if v not in (1, -1):
            raise ValueError('Direction must be 1 or -1')
        return v


    
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    email: EmailStr | None = None