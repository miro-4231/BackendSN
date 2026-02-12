from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlmodel import update, select
from sqlalchemy import func, text
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app import schemas, model, oauth2, utils
from typing import Annotated, List

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

        print(statement.compile(compile_kwargs={"literal_binds": True}))

        result = await session.execute(statement)
        posts = result.scalars().all()
        return posts

    