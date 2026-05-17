from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import URL, Click
from app.utils import anonymize_ip
from app.rate_limiter import limiter

router = APIRouter()

@router.get("/{short_code}")
@limiter.limit("60/minute")
async def redirect(short_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    raw_ip = request.client.host if request.client else None
    client_ip = anonymize_ip(raw_ip)
    _ua = request.headers.get("user-agent")
    user_agent = _ua[:512] if _ua else None
    click = Click(url_id=url.id, ip_address=client_ip, user_agent=user_agent)
    db.add(click)
    await db.commit()
    return RedirectResponse(url=str(url.original_url), status_code=302)
