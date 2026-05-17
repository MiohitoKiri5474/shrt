from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import URL, Click, User
from app.schemas import URLCreate, URLOut, StatsOut
from app.services.auth import get_unique_short_code
from app.routers.auth import get_current_user

router = APIRouter()

@router.post("", response_model=URLOut, status_code=201)
async def create_url(
    data: URLCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.custom_code:
        result = await db.execute(select(URL).where(URL.short_code == data.custom_code))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Short code already taken")
        code = data.custom_code
    else:
        try:
            code = await get_unique_short_code(db)
        except RuntimeError:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable. Please try again later.")
    url = URL(user_id=current_user.id, original_url=str(data.original_url), short_code=code)
    db.add(url)
    await db.commit()
    await db.refresh(url)
    click_count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
    item = URLOut.model_validate(url)
    item.click_count = click_count or 0
    return item

@router.get("", response_model=list[URLOut])
async def list_urls(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(URL).where(URL.user_id == current_user.id).order_by(URL.created_at.desc())
    )
    urls = result.scalars().all()
    out = []
    for url in urls:
        count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
        item = URLOut.model_validate(url)
        item.click_count = count or 0
        out.append(item)
    return out

@router.delete("/{url_id}", status_code=204)
async def delete_url(
    url_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(URL).where(URL.id == url_id, URL.user_id == current_user.id))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    await db.delete(url)
    await db.commit()

@router.get("/{url_id}/stats", response_model=StatsOut)
async def get_stats(
    url_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(URL).where(URL.id == url_id, URL.user_id == current_user.id))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    total = await db.scalar(select(func.count()).where(Click.url_id == url_id)) or 0
    date_rows = await db.execute(
        select(func.date(Click.clicked_at), func.count())
        .where(Click.url_id == url_id)
        .group_by(func.date(Click.clicked_at))
    )
    clicks_by_date = {str(row[0]): row[1] for row in date_rows}
    return StatsOut(
        url_id=url.id,
        short_code=url.short_code,
        original_url=url.original_url,
        total_clicks=total,
        clicks_by_date=clicks_by_date,
    )
