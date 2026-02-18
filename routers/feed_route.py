from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlmodel import update, select
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import Annotated, List
import asyncio
from pgvector.sqlalchemy import Vector # Ensure you use the Vector type
from app.encoder import encode_text

async def semantic_search(query_vector: list[float], session: AsyncSession, limit: int = 10, offset: int = 0):
    """
    Finds the most relevant posts using Cosine Distance.
    The HNSW index will automatically speed this up.
    """
    statement = (
        select(model.Posts)
        # Cosine distance: lower distance = higher similarity
        .options(joinedload(model.Posts.author))
        .order_by(model.Posts.embedding.cosine_distance(query_vector))
        .limit(limit)
        .offset(offset)
    )
    
    result = await session.execute(statement)
    # .scalars() returns the Post objects directly
    return result.scalars().all()

async def get_hot_posts_query(session: AsyncSession, limit: int, offset: int):
    # Move the score math here so both routes can use it
    score_expression = (
        func.log(func.greatest(func.abs(model.Posts.votes), 1)) +
        (func.extract('epoch', model.Posts.created_at) - 1334845200) / 45000
    ).label("hot_score")

    statement = (
        select(model.Posts)
        .options(joinedload(model.Posts.author))
        .order_by(score_expression.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(statement)
    return result.scalars().all()

router = APIRouter(prefix='/feed', tags=['Feed'])

@router.get('/hot', status_code=status.HTTP_200_OK, response_model=List[schemas.Post_out])
async def get_hot_feed(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[AsyncSession, Depends(utils.get_db)], 
                        limit: int = Query(default=10, le=100),
                        offset: int = Query(default=0, le=1000)):
        score_expression = (
            func.log(func.greatest(func.abs(model.Posts.votes),1))+
            (func.extract('epoch',model.Posts.created_at) - 1334845200)/45000
        ).label("hot_score")

        statement = (
        select(model.Posts)
        .options(joinedload(model.Posts.author)) # Efficiently gets the author info
        #.where(model.Posts. == False)
        .order_by(score_expression.desc())     # Use the math here
        .limit(limit)
        .offset(offset)
        )

        result = await session.execute(statement)
        posts = result.scalars().all()
        return posts

@router.get('/similar/{query}', status_code=status.HTTP_200_OK, response_model=List[schemas.Post_out])
async def get_similar_feed(current_user: Annotated[schemas.User_out, Depends(oauth2.get_current_user)],
                        session: Annotated[AsyncSession, Depends(utils.get_db)], 
                        query: str,
                        limit: int = Query(default=10, le=100),
                        offset: int = Query(default=0, le=1000)):
            
    loop = asyncio.get_event_loop()
    query_vector = await loop.run_in_executor(
        None, 
        encode_text, 
        query
    )
    
    # 2. Query the DB using our semantic_search function
    posts = await semantic_search(query_vector, session, limit, offset)
    
    return posts

@router.get('/personalized', response_model=List[schemas.Post_out])
async def get_personalized_feed(
    current_user: Annotated[model.Users, Depends(oauth2.get_current_user)], # Use DB model
    session: Annotated[AsyncSession, Depends(utils.get_db)],
    limit: int = Query(10),
    offset: int = Query(0)
):
    if current_user.embedding is None:
        return await get_hot_posts_query(session, limit, offset)
        
    # Ensure semantic_search also has joinedload(model.Posts.author)!
    return await semantic_search(current_user.embedding, session, limit, offset)
