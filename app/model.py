from sqlmodel import Field, SQLModel, Index, SmallInteger, CheckConstraint, Relationship
from datetime import datetime
from sqlalchemy import func, Column, DateTime
from pydantic import EmailStr
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import Posts, Users, Comments

class Posts(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    content: str
    author_id: int = Field(foreign_key="users.id", index=True)
    published: bool = True
    votes: int = Field(default=0)
    comments_count: int = Field(default=0)
    created_at : datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            nullable=False
        )
    )
    modified_at : datetime|None = Field(
        sa_column=Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            onupdate=func.now()
        ),
        default=None
    )

    # The Python-side link back to the user
    author: "Users" = Relationship(back_populates="posts")
 
    
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
                sa_column=Column(DateTime(timezone=True),
                server_default=func.now(),
                nullable=False))

    # The Python-side link back to the posts
    posts: list["Posts"] = Relationship(back_populates="author")
    comments: list["Comments"] = Relationship(back_populates="author")
    
class Votes(SQLModel, table=True):
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    post_id: int | None = Field(default=None, foreign_key="posts.id", primary_key=True, ondelete="CASCADE")
    comment_id: int | None = Field(default=None, foreign_key="comments.id", primary_key=True, ondelete="CASCADE")
    direction: int = Field(sa_type=SmallInteger)
    is_super: bool = Field(default=False)
    created_at : datetime = Field(
                sa_column=Column(DateTime(timezone=True),
                server_default=func.now(),
                nullable=False))
    __table_args__ = (
        # Ensures that EITHER post_id is filled OR comment_id is filled, but not both/neither
        CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)",
            name="check_vote_target"
        ),
    )
    
class RefreshTokens(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    jti: str = Field( index=True)
    token_hash: str = Field(index=True)
    expires_at: datetime = Field(
                sa_column=Column(DateTime(timezone=True),
                server_default=func.now(),
                nullable=False))
    is_revoked: bool = Field()
    created_at : datetime = Field(
                sa_column=Column(DateTime(timezone=True),
                server_default=func.now(),
                nullable=False))

class Comments(SQLModel, table=True):
    id: int|None = Field(default=None, primary_key=True)
    content: str = Field(max_length=500)
    user_id:int = Field(foreign_key="users.id", index=True)
    post_id: int = Field(foreign_key="posts.id", ondelete="CASCADE", index=True)
    parent_id: int|None = Field(foreign_key="comments.id", ondelete="CASCADE", index=True)
    votes:int = Field(default=0)
    is_deleted: bool = Field(default=False)
    created_at : datetime = Field(
                sa_column=Column(DateTime(timezone=True),
                server_default=func.now(),
                nullable=False))
    modified_at : datetime|None = Field(
        sa_column=Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            onupdate=func.now()
        ),
        default=None
    )

    author: "Users" = Relationship(back_populates="comments")

    # replies: list["Comments"] = Relationship(
    #     sa_relationship_kwargs={
    #         "remote_side": 'Comments.id',
    #         # "cascade": "all, delete-orphan",
    #         "order_by": "desc(Comments.votes), desc(Comments.created_at)"
    #     }
    # )





