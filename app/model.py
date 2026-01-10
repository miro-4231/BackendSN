from sqlmodel import Field, SQLModel, Index, SmallInteger, CheckConstraint, Relationship
from datetime import datetime
from sqlalchemy import func
from pydantic import EmailStr

class Posts(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    author_id: int = Field(foreign_key="users.id", index=True)
    published: bool = True
    votes: int = Field(default=0)
    created_at : datetime = Field(
        sa_column_kwargs={"server_default": func.now()}
    )
    modified_at : datetime|None = Field(
        sa_column_kwargs={"onupdate": func.now()}, default=None)

    # The Python-side link back to the user
    author: Users = Relationship(back_populates="posts")
    
    __table_args__ = (Index("ix_posts_author_created", "author_id", "created_at"),)
    
class Users(SQLModel, table=True):

    __table_args__ = (
        CheckConstraint("super_vote_balance >= 0", name="check_super_vote_positive"),
    )

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, max_length=18, index=True)
    email: EmailStr = Field(unique=True, index=True)
    password: str = Field()
    super_vote_balance: int = Field(default=5)
    created_at : datetime = Field(
        sa_column_kwargs={"server_default": func.now()}
    )

    # The Python-side link back to the posts
    posts: list[Posts] = Relationship(back_populates="author")
    
class Votes(SQLModel, table=True):
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    post_id: int = Field(foreign_key="posts.id", primary_key=True)
    direction: int = Field(sa_type=SmallInteger)
    is_super: bool = Field(default=False)
    created_at : datetime = Field(
        sa_column_kwargs={"server_default": func.now()}
    )
    
class RefreshTokens(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    jti: str = Field( index=True)
    token_hash: str = Field(index=True)
    expires_at: datetime = Field(index=True)
    is_revoked: bool = Field()
    created_at : datetime = Field(
        sa_column_kwargs={"server_default": func.now()}
    )



