from fastapi import APIRouter, status, HTTPException, Depends
from sqlmodel import update
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import Annotated

router = APIRouter(prefix="/posts", tags=["Comment"])

@router.post("/{post_id}/comments", status_code=status.HTTP_201_CREATED, response_model=schemas.CommentOut)
async def create_comment(post_id: int, comment_in: schemas.Comment_in,
                        current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[AsyncSession, Depends(utils.get_db)]):

    # Check if post exists
    post_target = await session.get(model.Posts, post_id)
    
    if not post_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id: {post_id} not found"
        )

    if comment_in.parent_id:
        comment_target = await session.get(model.Comments, comment_in.parent_id)
        if not comment_target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Comment with id: {comment_in.parent_id} not found"
            )
    
    # Update comment count
    await session.execute(
        update(model.Posts)
        .where(model.Posts.id == post_id)
        .values(comments_count=model.Posts.comments_count + 1)
    )


    # Create new comment
    new_comment = model.Comments(
        content=comment_in.content,
        user_id=current_user.id,
        post_id=post_id,
        parent_id=comment_in.parent_id
    )
    session.add(new_comment)
    await session.commit()
    await session.refresh(new_comment)
    return new_comment

@router.put("/comments", status_code=status.HTTP_200_OK, response_model=schemas.CommentOut)
async def edit_comment( comment_in: schemas.Comment_edit,
                        current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[AsyncSession, Depends(utils.get_db)]):
        
        # Check if the comment exists
        comment_target = await session.get(model.Comments, comment_in.id)

        if not comment_target :
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Comment with id: {comment_in.id} not found"
            )

        if comment_target.user_id != current_user.id : 
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Not authorized"
            )
        
        await session.execute(
            update(model.Comments)
            .where(model.Comments.id == comment_in.id)
            .values(content=comment_in.content)
        )
        await session.commit()
        await session.refresh(comment_target)
        return comment_target

@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(comment_id: int,
                         current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                         session: Annotated[AsyncSession, Depends(utils.get_db)]):

        # Check if the comment exists
        comment_target = await session.get(model.Comments, comment_id)

        if not comment_target :
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Comment with id: {comment_id} not found"
            )

        if comment_target.user_id != current_user.id : 
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Not authorized"
            )

        comment_target.content = "[deleted]"
        comment_target.is_deleted = True
        comment_target.user_id = None
        
        await session.execute(
            update(model.Posts)
            .where(model.Posts.id == comment_target.post_id)
            .values(comments_count=model.Posts.comments_count - 1)
        )
        
        # await session.delete(comment_target)
        await session.commit()
