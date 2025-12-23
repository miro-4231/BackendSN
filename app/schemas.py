from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Post(BaseModel):
    title: str 
    content: str
    published: Optional[bool] = True
    
    
class Post_return(Post):
    id: int
    created_at: datetime