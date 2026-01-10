from fastapi import APIRouter, status, HTTPException, Query, Depends
from sqlmodel import select, update, desc
from sqlmodel import Session
from app import schemas, model, oauth2, utils
from typing import List, Annotated


router = APIRouter(prefix="/vote", tags=["Voting"])

SUPER_VOTE_MULTIPLIER = 10

@router.post("/{post_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def case_vote(post_id: int, vote_in: schemas.VoteCreate,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[Session, Depends(utils.get_db)]):
    
    post_target = session.get(model.Posts, post_id)
    if not post_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id: {post_id} not found"
        )
    
    vote_target = session.get(model.Votes, (current_user.id, post_id))
    if vote_target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="You have already voted for this post"
        )

    # Handle Super Vote Balance Check
    if vote_in.is_super:
        # Fetch the actual database object
        user_db = session.get(model.Users, current_user.id)
        
        if user_db.super_vote_balance < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Insufficient super votes"
            )
        
        # Atomic decrement
        user_db.super_vote_balance = model.Users.super_vote_balance - 1
        session.add(user_db)

    # Atomic Vote Update on Post
    multiplier = SUPER_VOTE_MULTIPLIER if vote_in.is_super else 1
    change = vote_in.direction * multiplier
    
    post_target.votes = model.Posts.votes + change
    session.add(post_target)

    # Create new vote
    new_vote = model.Votes(
        user_id=current_user.id, 
        post_id=post_id, 
        direction=vote_in.direction, 
        is_super=vote_in.is_super
    )
    session.add(new_vote)
    
    session.commit()


@router.delete("/{post_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vote(post_id: int,
                    current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                    session: Annotated[Session, Depends(utils.get_db)]):
    
    post_target = session.get(model.Posts, post_id)
    if not post_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Post with id: {post_id} not found"
        )
    
    vote_target = session.get(model.Votes, (current_user.id, post_id))
    if not vote_target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Vote not found"
        )
    
    # Calculate the change to reverse
    multiplier = SUPER_VOTE_MULTIPLIER if vote_target.is_super else 1
    change = vote_target.direction * multiplier
    
    # Atomic update to post votes
    post_target.votes = model.Posts.votes - change
    session.add(post_target)
    
    # Refund super vote if applicable
    if vote_target.is_super:
        user_db = session.get(model.Users, current_user.id)
        user_db.super_vote_balance = model.Users.super_vote_balance + 1
        session.add(user_db)
    
    session.delete(vote_target)
    session.commit()