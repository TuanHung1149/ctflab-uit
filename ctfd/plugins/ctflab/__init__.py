"""CTFLab plugin - HTB-style isolated Docker lab instances with OpenVPN access."""

from CTFd.plugins import register_plugin_assets_directory
from CTFd.plugins.challenges import CHALLENGE_CLASSES


def load(app):
    """Register the CTFLab plugin with CTFd."""
    from .challenge_type import CTFLabChallenge
    from .expire import start_expire_thread
    from .routes import ctflab_bp

    app.register_blueprint(ctflab_bp)
    CHALLENGE_CLASSES["ctflab"] = CTFLabChallenge
    register_plugin_assets_directory(app, base_path="/plugins/ctflab/assets/")

    with app.app_context():
        from CTFd.models import db

        db.create_all()

    start_expire_thread(app)
