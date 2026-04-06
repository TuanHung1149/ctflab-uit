from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.box import Box
from app.schemas.box import BoxDetail, BoxResponse

router = APIRouter()


@router.get("/", response_model=list[BoxResponse])
async def list_boxes(db: AsyncSession = Depends(get_db)) -> list[BoxResponse]:
    result = await db.execute(select(Box).where(Box.is_active.is_(True)).order_by(Box.id))
    boxes = result.scalars().all()
    return [BoxResponse.model_validate(b) for b in boxes]


@router.get("/{slug}", response_model=BoxDetail)
async def get_box(slug: str, db: AsyncSession = Depends(get_db)) -> BoxDetail:
    result = await db.execute(select(Box).where(Box.slug == slug))
    box = result.scalar_one_or_none()

    if box is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Box not found",
        )

    return BoxDetail.model_validate(box)
