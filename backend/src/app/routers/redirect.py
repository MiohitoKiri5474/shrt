import asyncio
import logging
import re
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import URL, Click
from app.utils import anonymize_ip, is_expired
from app.rate_limiter import limiter, get_real_ip
from app.schemas import SSRFBlockedError, SSRFDNSError, validate_no_ssrf, _SSRF_EXECUTOR, _SSRF_CHECK_TIMEOUT_S

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/{short_code}")
@limiter.limit("60/minute")
async def redirect(
    request: Request,
    short_code: str = Path(..., max_length=16, pattern=r"^[a-zA-Z0-9_-]+$"),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail="Short URL not found")
    if is_expired(url.expires_at):
        return RedirectResponse(url=f"/expired?code={short_code}", status_code=302)
    if url.password_hash is not None:
        return RedirectResponse(url=f"/p/{short_code}", status_code=302)
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(_SSRF_EXECUTOR, validate_no_ssrf, str(url.original_url)),
            timeout=_SSRF_CHECK_TIMEOUT_S,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="URL destination temporarily unreachable")
    except SSRFDNSError:
        raise HTTPException(status_code=503, detail="URL destination temporarily unreachable")
    except SSRFBlockedError as e:
        logger.warning("SSRF check blocked redirect for short_code %s: %s", short_code, e.blocked_addr)
        raise HTTPException(status_code=400, detail="URL destination is no longer valid")
    except ValueError:
        raise HTTPException(status_code=400, detail="URL destination is no longer valid")
    raw_ip = get_real_ip(request)
    client_ip = anonymize_ip(raw_ip)
    _ua = request.headers.get("user-agent")
    user_agent = re.sub(r'[^\x20-\x7E]', '', _ua)[:512] if _ua else None
    click = Click(url_id=url.id, ip_address=client_ip, user_agent=user_agent)
    db.add(click)
    await db.commit()
    return RedirectResponse(url=str(url.original_url), status_code=302)
