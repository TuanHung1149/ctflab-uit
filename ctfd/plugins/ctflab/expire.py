"""Background thread to auto-expire old instances."""

import logging
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def expire_loop(app):
    """Run inside a background thread.  Check every 60 seconds for expired instances."""
    while True:
        time.sleep(60)
        try:
            with app.app_context():
                from CTFd.models import db

                from .docker_utils import DockerManager
                from .models import LabInstance

                expired = LabInstance.query.filter(
                    LabInstance.status == "running",
                    LabInstance.expires_at < datetime.utcnow(),
                ).all()

                if expired:
                    mgr = DockerManager()
                    for inst in expired:
                        logger.info(
                            "Auto-expiring instance %d (slot %d)",
                            inst.id,
                            inst.slot,
                        )
                        try:
                            mgr.destroy_instance(
                                inst.container_id, inst.network_id
                            )
                        except Exception:
                            pass
                        inst.status = "expired"
                    db.session.commit()
        except Exception:
            logger.exception("Expire loop error")


def start_expire_thread(app):
    """Spawn the daemon thread that garbage-collects expired instances."""
    t = threading.Thread(target=expire_loop, args=(app,), daemon=True)
    t.start()
    logger.info("Instance expire thread started")
