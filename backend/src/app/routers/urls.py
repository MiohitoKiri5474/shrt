import asyncio
import io
import logging
import re
import segno
from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import URL, Click, User
from app.schemas import SSRFBlockedError, SSRFDNSError, URLCreate, URLOut, URLUpdate, StatsOut, PasswordVerify, UnlockOut, validate_no_ssrf, _SSRF_EXECUTOR, _SSRF_CHECK_TIMEOUT_S
from app.services.auth import get_unique_short_code, hash_password, verify_password
from app.routers.auth import get_current_user
from app.rate_limiter import limiter, get_real_ip
from app.utils import anonymize_ip

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("", response_model=URLOut, status_code=201)
@limiter.limit("20/minute")
async def create_url(
    request: Request,
    data: URLCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(_SSRF_EXECUTOR, validate_no_ssrf, str(data.original_url)),
            timeout=_SSRF_CHECK_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="URL destination temporarily unreachable")
    except SSRFDNSError:
        raise HTTPException(status_code=503, detail="URL destination temporarily unreachable")
    except SSRFBlockedError as e:
        logger.warning("SSRF check blocked URL for user %s: %s", current_user.id, e.blocked_addr)
        raise HTTPException(
            status_code=422,
            detail=[{"loc": ["body", "original_url"], "msg": str(e), "type": "value_error"}],
        )
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
    url = URL(
        user_id=current_user.id,
        original_url=str(data.original_url),
        short_code=code,
        password_hash=hash_password(data.password) if data.password else None,
    )
    db.add(url)
    await db.commit()
    await db.refresh(url)
    click_count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
    return URLOut.from_orm_with_clicks(url, click_count or 0)

@router.get("", response_model=list[URLOut])
@limiter.limit("100/minute")
async def list_urls(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await db.execute(
        select(URL, func.count(Click.id).label("click_count"))
        .outerjoin(Click, Click.url_id == URL.id)
        .where(URL.user_id == current_user.id)
        .group_by(URL.id)
        .order_by(URL.created_at.desc())
    )
    return [URLOut.from_orm_with_clicks(url, click_count or 0) for url, click_count in rows]

@router.patch("/{url_id}", response_model=URLOut)
@limiter.limit("30/minute")
async def update_url(
    request: Request,
    url_id: int,
    data: URLUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(URL).where(URL.id == url_id, URL.user_id == current_user.id))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    if data.short_code != url.short_code:
        conflict = await db.execute(select(URL).where(URL.short_code == data.short_code))
        if conflict.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Short code already taken")
        url.short_code = data.short_code
    if data.remove_password:
        url.password_hash = None
    elif data.password:
        url.password_hash = hash_password(data.password)
    url.expires_at = data.expires_at
    await db.commit()
    await db.refresh(url)
    click_count = await db.scalar(select(func.count()).where(Click.url_id == url.id))
    return URLOut.from_orm_with_clicks(url, click_count or 0)


@router.delete("/{url_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_url(
    request: Request,
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

@router.post("/{short_code}/unlock", response_model=UnlockOut)
@limiter.limit("10/minute")
async def unlock_url(
    request: Request,
    short_code: str,
    data: PasswordVerify,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if url.password_hash is None:
        raise HTTPException(status_code=400, detail="This URL is not password protected")
    if not verify_password(data.password, url.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(_SSRF_EXECUTOR, validate_no_ssrf, str(url.original_url)),
            timeout=_SSRF_CHECK_TIMEOUT_S,
        )
    except (asyncio.TimeoutError, SSRFDNSError, SSRFBlockedError, ValueError):
        raise HTTPException(status_code=400, detail="URL destination is no longer valid")
    raw_ip = get_real_ip(request)
    client_ip = anonymize_ip(raw_ip)
    _ua = request.headers.get("user-agent")
    user_agent = re.sub(r'[^\x20-\x7E]', '', _ua)[:512] if _ua else None
    click = Click(url_id=url.id, ip_address=client_ip, user_agent=user_agent)
    db.add(click)
    await db.commit()
    return UnlockOut(redirect_url=str(url.original_url))


@router.get("/{url_id}/stats", response_model=StatsOut)
@limiter.limit("60/minute")
async def get_stats(
    request: Request,
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

@router.get(
    "/{short_code}/qr",
    responses={200: {"content": {"image/png": {}}}},
)
@limiter.limit("60/minute")
async def get_qr_code(
    request: Request,
    short_code: str = Path(..., max_length=16, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(URL).where(URL.short_code == short_code, URL.user_id == current_user.id)
    )
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="URL not found")
    short_url = f"{str(request.base_url).rstrip('/')}/{url.short_code}"
    buffer = io.BytesIO()
    segno.make_qr(short_url, error="m").save(buffer, kind="png", scale=8, border=4)
    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="qr-{url.short_code}.png"',
            "Cache-Control": "private, max-age=86400",
        },
    )
