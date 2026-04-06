"""Manages slot allocation for user instances.

Each slot N determines:
- Docker network subnet: 10.100.N.0/24
- VPN client IP: 10.200.N.2

Slots range from 1 to settings.MAX_SLOT (default 50).
"""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.instance import Instance, InstanceStatus

# Statuses that indicate a slot is actively in use
_ACTIVE_STATUSES = frozenset({
    InstanceStatus.PENDING.value,
    InstanceStatus.STARTING.value,
    InstanceStatus.RUNNING.value,
    InstanceStatus.STOPPING.value,
})


async def allocate_slot(db: AsyncSession) -> int:
    """Find and return the lowest available slot from 1..MAX_SLOT.

    A slot is considered "in use" when an instance references it and
    its status is not STOPPED or ERROR.

    Raises:
        HTTPException 503: When all slots are occupied.
    """
    stmt = (
        select(Instance.slot)
        .where(
            Instance.slot.isnot(None),
            Instance.status.in_(list(_ACTIVE_STATUSES)),
        )
    )
    result = await db.execute(stmt)
    used_slots: set[int] = {row[0] for row in result.all()}

    for candidate in range(1, settings.MAX_SLOT + 1):
        if candidate not in used_slots:
            return candidate

    raise HTTPException(
        status_code=503,
        detail="No available slots. Please try again later.",
    )


async def release_slot(db: AsyncSession, slot: int) -> None:
    """Release a slot.

    This is a no-op because a slot is implicitly released when the
    owning instance transitions to STOPPED or ERROR status.
    The function exists as a documented extension point for future
    cleanup logic (e.g., audit logging).
    """
