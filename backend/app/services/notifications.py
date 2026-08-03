"""Firebase Cloud Messaging helpers for broadcast mobile notifications."""

from pathlib import Path
import structlog
from firebase_admin import credentials, get_app, initialize_app, messaging

from app.core.config import get_settings

logger = structlog.get_logger()
MOBILE_TOPIC = "tnpsc_all"


def _firebase_app():
    """Return the Firebase app only when server credentials are configured."""
    credentials_path = get_settings().firebase_credentials_path
    if not credentials_path:
        return None
    path = Path(credentials_path)
    if not path.is_file():
        logger.warning("fcm_disabled_missing_credentials", path=str(path))
        return None
    try:
        return get_app()
    except ValueError:
        return initialize_app(credentials.Certificate(str(path)))


def send_topic_notification(title: str, body: str, notification_type: str, resource_id: str) -> None:
    """Send a non-fatal, deep-linkable alert to all opted-in TNPSC users."""
    try:
        app = _firebase_app()
        if app is None:
            return
        message = messaging.Message(
            topic=MOBILE_TOPIC,
            notification=messaging.Notification(title=title, body=body),
            data={"type": notification_type, "resource_id": resource_id},
        )
        message_id = messaging.send(message, app=app)
        logger.info("fcm_topic_sent", message_id=message_id, type=notification_type)
    except Exception:
        # A Firebase outage must never make publishing a PDF or test fail.
        logger.exception("fcm_topic_send_failed", type=notification_type)
