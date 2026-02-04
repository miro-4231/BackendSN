from sqlalchemy.orm import joinedload
from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlmodel import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import Annotated, List

router = APIRouter(prefix="/comments", tags=["Comment"])

SUPER_VOTE_MULTIPLIER = 10

@router.put("/edit", status_code=status.HTTP_200_OK, response_model=schemas.Comment_out)
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

@router.delete("/delete/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
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
        #comment_target.user_id = 
        
        await session.execute(
            update(model.Posts)
            .where(model.Posts.id == comment_target.post_id)
            .values(comments_count=model.Posts.comments_count - 1)
        )
        
        # await session.delete(comment_target)
        await session.commit()

@router.post("/vote/{comment_id}", status_code=status.HTTP_201_CREATED)
async def vote_comment(comment_id: int, vote_in: schemas.VoteCreate,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[AsyncSession, Depends(utils.get_db)]):

    # Check if post exists
    comment_target = await session.get(model.Comments, comment_id)
    
    if not comment_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"comment with id: {comment_id} not found"
        )

    
    # Check if user has already voted for this post
    vote_target = await session.get(model.Votes, (current_user.id, None, comment_id))
    if vote_target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Already voted"
        )

    # Handle Super Vote Balance Check
    if vote_in.is_super:

        # Atomic decrement
        user_update = await session.execute(
                update(model.Users)
                .where(model.Users.id == current_user.id)
                .where(model.Users.super_vote_balance >= 1)
                .values(super_vote_balance=model.Users.super_vote_balance - 1)
            )
        if user_update.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Insufficient super votes"
            )
        multiplier = SUPER_VOTE_MULTIPLIER
    else:
        multiplier = 1

    # Atomic Vote Update on Post
    change = vote_in.direction * multiplier

    # Atomic update to post votes
    await session.execute(
            update(model.Comments)
            .where(model.Comments.id == comment_id)
            .values(votes=model.Comments.votes + change)
        )

    # Create new vote
    new_vote = model.Votes(
        user_id=current_user.id, 
        comment_id=comment_id, 
        direction=vote_in.direction, 
        is_super=vote_in.is_super
    )
    session.add(new_vote)
    await session.commit()


@router.get("/{post_id}", status_code=status.HTTP_200_OK, response_model=List[schemas.Comment_out])
async def get_comments(post_id:int, session:Annotated[AsyncSession, Depends(utils.get_db)],
    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
    limit: int = Query(default=10, gt=0, le=100, description="Maximum number of items to return"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip")):

    comments = await session.execute(select(model.Comments).where(model.Comments.post_id == post_id).options(joinedload(model.Comments.author)).offset(offset).limit(limit))
    return comments.scalars().all()

@router.post("/{post_id}/create", status_code=status.HTTP_201_CREATED, response_model=schemas.Comment_out)
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
        
        # await session.refresh(comment_target, ['replies', 'author'])
    
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
    await session.refresh(new_comment, ['author'])#, 'replies'])
    return new_comment

