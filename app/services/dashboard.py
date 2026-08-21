from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.models.audit import DashboardRequest
from app.models.organization import Organization
from app.schemas.dashboard import DashboardRequestCreate, DashboardRequestRead


async def create_dashboard_request(
    session: AsyncSession,
    principal: Principal,
    payload: DashboardRequestCreate,
) -> DashboardRequestRead:
    org = await session.scalar(select(Organization).where(Organization.external_id == principal.organization_id))
    if not org or not org.premium_enabled:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Dashboard requests require a premium organization")
    request = DashboardRequest(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        payload=payload.model_dump(mode="json"),
        status="queued",
    )
    session.add(request)
    await session.commit()
    await session.refresh(request)
    return DashboardRequestRead(id=request.id, status=request.status)
