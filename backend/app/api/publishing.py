import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.deps import get_current_user, get_db
from backend.app.models.paper import Paper
from backend.app.models.published_article import PublishedArticle
from backend.app.models.user import User
from backend.app.schemas.publishing import PublishRequest, PublishResponse

router = APIRouter(prefix="/publish", tags=["publishing"])
logger = structlog.get_logger()


@router.post("/devto", response_model=PublishResponse, status_code=status.HTTP_201_CREATED)
async def publish_to_devto(
    body: PublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    paper_result = await db.execute(
        select(Paper).where(Paper.id == body.paper_id, Paper.user_id == current_user.id)
    )
    paper = paper_result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")

    if paper.paper_type != "blog":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only blog papers can be published to dev.to",
        )

    # Placeholder: actual dev.to API integration goes here
    article = PublishedArticle(
        paper_id=paper.id,
        platform="devto",
        platform_article_id=None,
        published_url=f"https://dev.to/draft/{paper.id}",
        series_name=paper.title,
        part_number=body.part_number,
        status="draft" if not body.published else "published",
    )
    db.add(article)
    await db.flush()
    await db.refresh(article)

    logger.info("article_published", article_id=str(article.id), platform="devto")
    return PublishResponse.model_validate(article)


@router.get("/status/{article_id}", response_model=PublishResponse)
async def get_publish_status(
    article_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PublishedArticle).where(PublishedArticle.id == article_id)
    )
    article = result.scalar_one_or_none()
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Published article not found"
        )
    return PublishResponse.model_validate(article)
