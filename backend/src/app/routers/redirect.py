from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import URL, Click
from app.utils import anonymize_ip

router = APIRouter()

@router.get("/{short_code}")
async def redirect(short_code: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    raw_ip = request.client.host if request.client else None
    client_ip = anonymize_ip(raw_ip)
    user_agent = (request.headers.get("user-agent") or "")[:512]
    click = Click(url_id=url.id, ip_address=client_ip, user_agent=user_agent)
    db.add(click)
    await db.commit()
    return RedirectResponse(url=url.original_url, status_code=302)
