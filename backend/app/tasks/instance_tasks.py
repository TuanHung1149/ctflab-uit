"""Instance lifecycle tasks: create, destroy, reset."""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.instance import Instance, InstanceStatus
from app.models.box import Box
from app.models.challenge import Challenge
from app.models.vpn_config import VpnConfig
from app.services.docker_service import DockerService
from app.services.flag_generator import generate_flags
from app.services.openvpn_service import OpenVPNService
from app.services.slot_manager import allocate_slot

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL)
_session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _get_db() -> AsyncSession:
    return _session_factory()


async def create_instance_task(ctx: dict, instance_id: int) -> None:
    """Full orchestration: network -> container -> VPN -> update DB."""
    db = await _get_db()
    docker_svc = DockerService()
    ovpn_svc = OpenVPNService()

    try:
        instance = await db.get(Instance, instance_id)
        if not instance:
            logger.error(f"Instance {instance_id} not found")
            return

        box_result = await db.execute(select(Box).where(Box.id == instance.box_id))
        box = box_result.scalar_one_or_none()
        if not box:
            logger.error(f"Box {instance.box_id} not found")
            return

        slot = instance.slot
        instance.status = InstanceStatus.STARTING
        await db.commit()

        # Generate random flags
        challenges_result = await db.execute(
            select(Challenge).where(Challenge.box_id == box.id).order_by(Challenge.order)
        )
        challenges = challenges_result.scalars().all()
        prefixes = [c.flag_prefix for c in challenges]
        flags = generate_flags(prefixes)
        instance.flags_json = json.dumps(flags)

        # Create isolated Docker network
        network_id, network_name = await docker_svc.create_network(slot)
        instance.network_id = network_id
        instance.network_name = network_name

        # Run box container
        env_overrides = json.loads(box.env_json) if box.env_json else {}
        container_id, container_ip = await docker_svc.run_box(
            image=box.docker_image,
            slot=slot,
            network_name=network_name,
            flags=flags,
            env_overrides=env_overrides,
        )
        instance.container_id = container_id
        instance.container_ip = container_ip

        # Generate OpenVPN client config
        try:
            ovpn_config_text = await ovpn_svc.create_client(slot)
            vpn = VpnConfig(
                user_id=instance.user_id,
                instance_id=instance.id,
                slot=slot,
                client_config_text=ovpn_config_text,
                is_active=True,
            )
            db.add(vpn)
        except Exception as e:
            logger.warning(f"OpenVPN setup failed (non-fatal): {e}")

        # Finalize
        instance.status = InstanceStatus.RUNNING
        instance.started_at = datetime.utcnow()
        instance.expires_at = datetime.utcnow() + timedelta(
            hours=settings.INSTANCE_LIFETIME_HOURS
        )
        await db.commit()
        logger.info(f"Instance {instance_id} is now RUNNING at {container_ip}")

    except Exception as e:
        logger.error(f"Failed to create instance {instance_id}: {e}")
        try:
            instance.status = InstanceStatus.ERROR
            await db.commit()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def destroy_instance_task(ctx: dict, instance_id: int) -> None:
    """Tear down: stop container, remove network, revoke VPN, release slot."""
    db = await _get_db()
    docker_svc = DockerService()
    ovpn_svc = OpenVPNService()

    try:
        instance = await db.get(Instance, instance_id)
        if not instance:
            return

        instance.status = InstanceStatus.STOPPING
        await db.commit()

        # Remove container
        if instance.container_id:
            await docker_svc.stop_and_remove(instance.container_id)

        # Remove network
        if instance.network_id:
            await docker_svc.remove_network(instance.network_id)

        # Revoke VPN
        if instance.slot:
            try:
                await ovpn_svc.remove_client(instance.slot)
            except Exception:
                pass

        # Deactivate VPN config
        vpn_result = await db.execute(
            select(VpnConfig).where(VpnConfig.instance_id == instance.id)
        )
        vpn = vpn_result.scalar_one_or_none()
        if vpn:
            vpn.is_active = False

        instance.status = InstanceStatus.STOPPED
        instance.container_id = None
        instance.network_id = None
        await db.commit()
        logger.info(f"Instance {instance_id} destroyed")

    except Exception as e:
        logger.error(f"Failed to destroy instance {instance_id}: {e}")
        raise
    finally:
        await db.close()


async def reset_instance_task(ctx: dict, instance_id: int) -> None:
    """Call reset-state.sh inside the container to restore flags/files."""
    db = await _get_db()
    docker_svc = DockerService()

    try:
        instance = await db.get(Instance, instance_id)
        if not instance or not instance.container_id:
            return

        await docker_svc.exec_in_container(
            instance.container_id,
            ["/root/infinity/docker/reset-state.sh"],
        )
        logger.info(f"Instance {instance_id} reset complete")

    except Exception as e:
        logger.error(f"Failed to reset instance {instance_id}: {e}")
        raise
    finally:
        await db.close()
