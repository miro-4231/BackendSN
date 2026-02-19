from fastapi import APIRouter, status, HTTPException, Depends, BackgroundTasks
from sqlmodel import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import Annotated


router = APIRouter(prefix="/vote", tags=["Voting"])

SUPER_VOTE_MULTIPLIER = 10

@router.post("/{post_id}", status_code=status.HTTP_201_CREATED)
async def case_vote(post_id: int, vote_in: schemas.VoteCreate,
                    background_tasks: BackgroundTasks,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[AsyncSession, Depends(utils.get_db)]):

    # Check if post exists
    post_target = await session.get(model.Posts, post_id)
    
    if not post_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id: {post_id} not found"
        )

    
    statement = select(model.Votes).where(
    model.Votes.user_id == current_user.id,
    model.Votes.post_id == post_id
)
    result = await session.execute(statement)
    vote_target = result.scalar_one_or_none()
    if vote_target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Already voted"
        )

    if post_target.embedding:
        background_tasks.add_task(utils.run_background_update, current_user.id, post_target.embedding)

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
            update(model.Posts)
            .where(model.Posts.id == post_id)
            .values(votes=model.Posts.votes + change)
        )

    # Create new vote
    new_vote = model.Votes(
        user_id=current_user.id, 
        post_id=post_id, 
        direction=vote_in.direction, 
        is_super=vote_in.is_super,
        comment_id=None
    )
    session.add(new_vote)
    await session.commit()
        


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vote(post_id: int,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[AsyncSession, Depends(utils.get_db)]):

    post_target = await session.get(model.Posts, post_id)
    if not post_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id: {post_id} not found"
        )
    
    statement = select(model.Votes).where(
    model.Votes.user_id == current_user.id,
    model.Votes.post_id == post_id
    )
    result = await session.execute(statement)
    vote_target = result.scalar_one_or_none()
    if not vote_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Vote not found"
        )
    
    # Calculate the change to reverse
    multiplier = SUPER_VOTE_MULTIPLIER if vote_target.is_super else 1
    change = vote_target.direction * multiplier
    
    # Atomic update to post votes
    await session.execute(
        update(model.Posts)
        .where(model.Posts.id == post_id)
        .values(votes=model.Posts.votes - change)
    )
    
    # Refund super vote if applicable
    if vote_target.is_super:
        await session.execute(
            update(model.Users)
            .where(model.Users.id == current_user.id)
            .where(model.Users.super_vote_balance >= 0)
            .values(super_vote_balance=model.Users.super_vote_balance + 1)
        )
    
    await session.delete(vote_target)
    await session.commit()