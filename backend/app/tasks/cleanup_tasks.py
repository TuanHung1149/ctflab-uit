"""Cleanup tasks: expire old instances."""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.instance import Instance, InstanceStatus

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL)
_session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def expire_instances_task(ctx: dict) -> None:
    """Find instances past expires_at and enqueue destroy tasks."""
    async with _session_factory() as db:
        result = await db.execute(
            select(Instance).where(
                Instance.status == InstanceStatus.RUNNING,
                Instance.expires_at < datetime.utcnow(),
            )
        )
        expired = result.scalars().all()

        for instance in expired:
            logger.info(f"Expiring instance {instance.id} (slot {instance.slot})")
            await ctx["redis"].enqueue_job(
                "destroy_instance_task", instance.id
            )
