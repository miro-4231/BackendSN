from sqlmodel import Field, SQLModel
from datetime import datetime
from sqlalchemy import func
from pydantic import EmailStr

class Posts(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    published: bool = True
    created_at : datetime = Field(
        #default_factory=datetime.utcnow,
        sa_column_kwargs={
            "server_default" : func.now()
        })
    
class Users(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True)
    password: str = Field()
    created_at : datetime = Field(
        #default_factory=datetime.utcnow,
        sa_column_kwargs={
            "server_default" : func.now()
        })
    
    

