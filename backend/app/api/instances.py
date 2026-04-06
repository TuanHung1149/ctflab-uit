import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.box import Box
from app.models.instance import Instance, InstanceStatus
from app.models.vpn_config import VpnConfig
from app.models.user import User
from app.schemas.instance import InstanceCreate, InstanceResponse, VpnConfigResponse

# Docker and OpenVPN services will be imported once implemented:
# from app.services.docker_service import DockerService
# from app.services.openvpn_service import OpenVPNService

router = APIRouter()

ACTIVE_STATUSES = [
    InstanceStatus.PENDING.value,
    InstanceStatus.STARTING.value,
    InstanceStatus.RUNNING.value,
]


@router.post("/", response_model=InstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_instance(
    body: InstanceCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanceResponse:
    active_count_result = await db.execute(
        select(func.count(Instance.id)).where(
            Instance.user_id == user.id,
            Instance.status.in_(ACTIVE_STATUSES),
        )
    )
    active_count = active_count_result.scalar_one()

    if active_count >= settings.MAX_INSTANCES_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum active instances reached ({settings.MAX_INSTANCES_PER_USER})",
        )

    box_result = await db.execute(select(Box).where(Box.slug == body.box_slug))
    box = box_result.scalar_one_or_none()
    if box is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Box not found",
        )

    instance = Instance(
        user_id=user.id,
        box_id=box.id,
        status=InstanceStatus.PENDING.value,
    )
    db.add(instance)
    await db.flush()

    return InstanceResponse.model_validate(instance)


@router.get("/", response_model=list[InstanceResponse])
async def list_instances(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InstanceResponse]:
    result = await db.execute(
        select(Instance)
        .where(Instance.user_id == user.id)
        .order_by(Instance.created_at.desc())
    )
    instances = result.scalars().all()
    return [InstanceResponse.model_validate(i) for i in instances]


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InstanceResponse:
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    if instance.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return InstanceResponse.model_validate(instance)


@router.delete("/{instance_id}")
async def delete_instance(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    if instance.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # For MVP: set STOPPED directly. Later, set STOPPING and enqueue a destroy task.
    instance.status = InstanceStatus.STOPPED.value
    await db.flush()

    return {"status": "stopping"}


@router.post("/{instance_id}/reset")
async def reset_instance(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    if instance.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if instance.status != InstanceStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Instance is not running",
        )

    # For MVP: return acknowledgement. Later, enqueue a reset task via Arq worker.
    return {"status": "resetting"}


@router.get("/{instance_id}/vpn", response_model=VpnConfigResponse)
async def get_vpn_config(
    instance_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VpnConfigResponse:
    inst_result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = inst_result.scalar_one_or_none()

    if instance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found",
        )

    if instance.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    vpn_result = await db.execute(
        select(VpnConfig).where(VpnConfig.instance_id == instance_id)
    )
    vpn = vpn_result.scalar_one_or_none()

    if vpn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="VPN config not yet available",
        )

    filename = f"ctflab-{user.username}-slot{vpn.slot}.ovpn"
    return VpnConfigResponse(config_text=vpn.client_config_text, filename=filename)
