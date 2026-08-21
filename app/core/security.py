from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


@dataclass(frozen=True)
class Principal:
    user_id: str
    organization_id: str
    email: str | None = None


async def get_current_principal(
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_organization_id: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
    if settings.local_auth_enabled and not settings.is_production:
        if not x_dev_user_id or not x_dev_organization_id:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing local development auth headers")
        return Principal(user_id=x_dev_user_id, organization_id=x_dev_organization_id)

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    return await verify_firebase_token(token, settings)


async def verify_firebase_token(token: str, settings: Settings) -> Principal:
    try:
        import firebase_admin
        from firebase_admin import auth, credentials
    except ImportError as exc:  # pragma: no cover - dependency/runtime guard
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Firebase auth dependency is not installed") from exc

    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {"projectId": settings.firebase_project_id})
        claims = auth.verify_id_token(token, check_revoked=True)
    except Exception as exc:  # pragma: no cover - exercised with Firebase in deployed env
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid bearer token") from exc

    organization_id = claims.get("organization_id") or claims.get("org_id")
    if not organization_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Token is missing organization claim")
    return Principal(user_id=claims["uid"], organization_id=str(organization_id), email=claims.get("email"))
