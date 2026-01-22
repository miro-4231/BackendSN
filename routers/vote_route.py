from fastapi import APIRouter, status, HTTPException, Query, Depends
from sqlmodel import select, update, desc
from sqlmodel import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import List, Annotated


router = APIRouter(prefix="/vote", tags=["Voting"])

SUPER_VOTE_MULTIPLIER = 10

@router.post("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def case_vote(post_id: int, vote_in: schemas.VoteCreate,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[AsyncSession, Depends(utils.get_db)]):
    
    async with session.begin():
        # Check if post exists
        post_target = await session.get(model.Posts, post_id)
        
        if not post_target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Post with id: {post_id} not found"
            )
        
        # Check if user has already voted for this post
        vote_target = await session.get(model.Votes, (current_user.id, post_id))
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
                update(model.Posts)
                .where(model.Posts.id == post_id)
                .values(votes=model.Posts.votes + change)
            )

        # Create new vote
        new_vote = model.Votes(
            user_id=current_user.id, 
            post_id=post_id, 
            direction=vote_in.direction, 
            is_super=vote_in.is_super
        )
        session.add(new_vote)
        


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vote(post_id: int,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[AsyncSession, Depends(utils.get_db)]):
    
    async with session.begin():
        post_target = await session.get(model.Posts, post_id)
        if not post_target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Post with id: {post_id} not found"
            )
        
        vote_target = await session.get(model.Votes, (current_user.id, post_id))
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