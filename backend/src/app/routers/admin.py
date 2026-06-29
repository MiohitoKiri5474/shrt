from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models import URL, User
from app.schemas import AdminUserOut, AdminUserUpdate
from app.routers.auth import require_admin
from app.rate_limiter import limiter

router = APIRouter()


@router.get("/users", response_model=list[AdminUserOut])
@limiter.limit("60/minute")
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    rows = await db.execute(
        select(User, func.count(URL.id).label("url_count"))
        .outerjoin(URL, URL.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )
    out = []
    for user, url_count in rows:
        item = AdminUserOut.model_validate(user)
        item.url_count = url_count or 0
        out.append(item)
    return out


@router.patch("/users/{user_id}", response_model=AdminUserOut)
@limiter.limit("30/minute")
async def update_user_role(
    request: Request,
    user_id: int,
    body: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own admin role")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = body.is_admin
    await db.commit()
    await db.refresh(user)
    out = AdminUserOut.model_validate(user)
    url_count_result = await db.execute(
        select(func.count(URL.id)).where(URL.user_id == user.id)
    )
    out.url_count = url_count_result.scalar_one() or 0
    return out


@router.delete("/users/{user_id}", status_code=204)
@limiter.limit("30/minute")
async def delete_user(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        # Guard against an admin locking themselves out / orphaning their session.
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Relationship cascade ("all, delete") removes the user's URLs and their clicks.
    await db.delete(user)
    await db.commit()
