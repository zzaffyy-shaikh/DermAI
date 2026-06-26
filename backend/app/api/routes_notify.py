"""In-app notification center (polling). Any authenticated user sees their own."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..schemas import Notification
from ..services.notifications import notification_store
from .deps import CurrentUser, get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


class MarkReadRequest(BaseModel):
    ids: list[str] | None = None        # None = mark all read


class RegisterTokenRequest(BaseModel):
    token: str                          # Expo push token from the mobile app


@router.post("/register-token")
async def register_token(
    body: RegisterTokenRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    notification_store.register_token(user.uid, body.token)
    return {"ok": True}


@router.get("", response_model=list[Notification])
async def list_notifications(user: CurrentUser = Depends(get_current_user)) -> list[Notification]:
    return notification_store.list_for(user.uid)


@router.get("/unread_count")
async def unread_count(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"unread": notification_store.unread_count(user.uid)}


@router.post("/read")
async def mark_read(
    body: MarkReadRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    changed = notification_store.mark_read(user.uid, body.ids)
    return {"updated": changed, "unread": notification_store.unread_count(user.uid)}
