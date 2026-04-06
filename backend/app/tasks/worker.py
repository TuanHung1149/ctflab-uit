"""Arq worker configuration for background task processing."""
from arq.connections import RedisSettings
from app.config import settings


async def startup(ctx: dict) -> None:
    """Called when worker starts."""
    pass


async def shutdown(ctx: dict) -> None:
    """Called when worker shuts down."""
    pass


class WorkerSettings:
    functions = [
        "app.tasks.instance_tasks.create_instance_task",
        "app.tasks.instance_tasks.destroy_instance_task",
        "app.tasks.instance_tasks.reset_instance_task",
        "app.tasks.cleanup_tasks.expire_instances_task",
    ]
    cron_jobs = []  # Will add expire job later
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 300
