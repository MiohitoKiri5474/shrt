import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as PathParam, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import SharedFile, User
from app.rate_limiter import limiter
from app.routers.auth import get_current_user
from app.schemas import FileOut, FileUnlockOut, PasswordVerify
from app.services.auth import hash_password_async, verify_password_async
from app.services.file_access import create_file_access_token, verify_file_access_token
from app.utils import is_expired
from app.services.uploads import (
    IMAGE_QUOTA_BYTES,
    delete_blob,
    get_unique_file_code,
    image_quota_used,
    read_capped,
    save_blob,
    validate_upload,
)

logger = logging.getLogger(__name__)

router = APIRouter()
serve_router = APIRouter()


def _safe_filename(name: str) -> str:
    # Strip quotes/control chars — this becomes a raw Content-Disposition
    # header value, not a filesystem path (storage uses short_code, never
    # this string), so the only risk here is a malformed header, not traversal.
    cleaned = "".join(c for c in name if c.isprintable() and c not in '"\\')
    return cleaned or "download"


def _is_expired(shared_file: SharedFile) -> bool:
    return shared_file.kind == "file" and is_expired(shared_file.expires_at)


@router.post("", response_model=FileOut, status_code=201)
@limiter.limit("20/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    kind: str = Form(...),
    password: str | None = Form(None, min_length=6, max_length=128),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await read_capped(file)
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e))
    filename = file.filename or ""
    try:
        mime_type = validate_upload(kind, filename, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if kind == "image":
        used = await image_quota_used(db, current_user.id)
        if used + len(data) > IMAGE_QUOTA_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Uploading this image would exceed your 500MB image quota",
            )
    try:
        code = await get_unique_file_code(db)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable. Please try again later.")
    storage_path = save_blob(code, data)
    # expires_at is a naive DateTime column (no timezone=True) storing UTC —
    # asyncpg rejects a tz-aware datetime bound against a TIMESTAMP WITHOUT
    # TIME ZONE column, so strip tzinfo after computing in UTC.
    expires_at = (
        (datetime.now(timezone.utc) + timedelta(days=7)).replace(tzinfo=None) if kind == "file" else None
    )
    shared_file = SharedFile(
        user_id=current_user.id,
        short_code=code,
        kind=kind,
        original_filename=filename[:255],
        mime_type=mime_type,
        size_bytes=len(data),
        storage_path=storage_path,
        password_hash=await hash_password_async(password) if password else None,
        expires_at=expires_at,
    )
    db.add(shared_file)
    await db.commit()
    await db.refresh(shared_file)
    return FileOut.from_orm_with_password_flag(shared_file)


@router.get("", response_model=list[FileOut])
@limiter.limit("100/minute")
async def list_files(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SharedFile)
        .where(SharedFile.user_id == current_user.id)
        .order_by(SharedFile.created_at.desc())
    )
    return [FileOut.from_orm_with_password_flag(f) for f in result.scalars()]


@router.delete("/{file_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_file(
    request: Request,
    file_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SharedFile).where(SharedFile.id == file_id, SharedFile.user_id == current_user.id)
    )
    shared_file = result.scalar_one_or_none()
    if not shared_file:
        raise HTTPException(status_code=404, detail="File not found")
    delete_blob(shared_file.storage_path)
    await db.delete(shared_file)
    await db.commit()


@router.post("/{short_code}/unlock", response_model=FileUnlockOut)
@limiter.limit("10/minute")
async def unlock_file(
    request: Request,
    short_code: str,
    data: PasswordVerify,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharedFile).where(SharedFile.short_code == short_code))
    shared_file = result.scalar_one_or_none()
    if not shared_file:
        raise HTTPException(status_code=404, detail="File not found")
    if _is_expired(shared_file):
        raise HTTPException(status_code=410, detail="This file has expired")
    if shared_file.password_hash is None:
        raise HTTPException(status_code=400, detail="This file is not password protected")
    if not await verify_password_async(data.password, shared_file.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_file_access_token(short_code)
    return FileUnlockOut(download_url=f"/f/{short_code}?token={token}")


@serve_router.get("/{short_code}")
@limiter.limit("60/minute")
async def serve_file(
    request: Request,
    short_code: str = PathParam(..., max_length=16, pattern=r"^[a-zA-Z0-9_-]+$"),
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SharedFile).where(SharedFile.short_code == short_code))
    shared_file = result.scalar_one_or_none()
    if not shared_file:
        raise HTTPException(status_code=404, detail="File not found")
    if _is_expired(shared_file):
        raise HTTPException(status_code=404, detail="This file has expired")
    if shared_file.password_hash is not None:
        # No token at all means this is a visitor opening the share link cold
        # (e.g. pasted from a message) — send them to the same password gate
        # links use, mirroring redirect.py's unprotected-visit -> /p/{code}
        # behavior. A token that's present but wrong/expired (only reachable
        # by following a stale/tampered download_url) is a hard 401 instead.
        if token is None:
            return RedirectResponse(url=f"/p/{short_code}?type=file", status_code=302)
        if not verify_file_access_token(token, short_code):
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
    if not Path(shared_file.storage_path).exists():
        raise HTTPException(status_code=404, detail="File not found")
    disposition = "attachment" if shared_file.kind == "file" else "inline"
    filename = _safe_filename(shared_file.original_filename)
    return FileResponse(
        shared_file.storage_path,
        media_type=shared_file.mime_type,
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )
