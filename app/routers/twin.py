from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.api_responses import TwinQueryResponse
from app.services.rag import query_similar
from app.services.embedding import embedding_service

router = APIRouter(prefix="/twin", tags=["twin"])


@router.get("/query", response_model=TwinQueryResponse)
async def twin_query(
    cause: str = Query(..., description="URL-encoded cause description"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    results = await query_similar(db, cause, limit, embedding_service)
    return TwinQueryResponse(results=results)
