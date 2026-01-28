"""Dashboard event handler for capturing and streaming log events.

Enhanced for the unified demo to support:
- SMS message content display in activity timeline
- Image/media attachment previews
- Anchor-specific event routing
"""

import logging
import re
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Optional

from pydantic import BaseModel, Field

# Event queue for storing dashboard events
_event_queue: Optional[deque] = None
_queue_lock = Lock()

# Maximum number of events to keep in queue
MAX_EVENTS = 200


class MediaAttachment(BaseModel):
    """Model for media attachments (images, etc.) in SMS messages."""

    url: str
    content_type: str = "image/jpeg"
    filename: str = ""
    index: int = 0


class DashboardEvent(BaseModel):
    """Model for dashboard events with enhanced SMS support."""

    timestamp: str
    event_type: str
    conversation_id: Optional[str] = None
    channel: Optional[str] = None
    profile_id: Optional[str] = None
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    # Enhanced fields for SMS content display
    sms_body: Optional[str] = None
    media_attachments: list[MediaAttachment] = Field(default_factory=list)
    from_number: Optional[str] = None


# Pattern mapping for log message to event type
# Extended for all anchor scenarios
EVENT_PATTERNS = {
    # Standard events
    "USER MESSAGE": "user_message",
    "VOICE MESSAGE": "user_message",
    "SMS MESSAGE": "user_message",
    "MEMORY | Retrieved": "memory",
    "AI AGENT | Processing": "ai_processing",
    "AI RESPONSE": "ai_response",
    "HANDOFF": "handoff",
    "CONVERSATION | Started": "conversation_started",
    "INCOMING CALL": "call_started",
    "WEBSOCKET | Connected": "websocket_connected",
    "CALL SETUP": "call_setup",
    # Anchor 1 specific events
    "CONCURRENT": "concurrent_channel",
    "CROSS-CHANNEL": "cross_channel",
    "VOICE ACTIVE": "voice_active",
    "VOICE ENDED": "voice_ended",
    "PHOTO": "photo_analysis",
    "QUOTE": "quote_generated",
    # Enhanced SMS events
    "SMS RECEIVED": "sms_received",
    "SMS WITH MEDIA": "sms_with_media",
    # Anchor selection events
    "ANCHOR SELECTED": "anchor_selected",
    "ANCHOR SWITCHED": "anchor_switched",
}


class DashboardLogHandler(logging.Handler):
    """Custom logging handler that captures events for dashboard streaming."""

    def __init__(self) -> None:
        """Initialize the dashboard log handler."""
        super().__init__()
        self.setLevel(logging.INFO)

    def emit(self, record: logging.LogRecord) -> None:
        """Process log record and push to event queue."""
        try:
            # Only process logs from tac.* loggers and anchor/server loggers
            if not (
                record.name.startswith("tac.")
                or record.name.startswith("anchors.")
                or record.name == "__main__"
            ):
                return

            # Extract structured context from log record
            conversation_id = getattr(record, "conversation_id", None)
            profile_id = getattr(record, "profile_id", None)
            channel = getattr(record, "channel", None)

            # Determine event type from log message
            message = record.getMessage()
            event_type = self._determine_event_type(message, record.levelname)

            # Skip if we can't determine event type
            if not event_type:
                return

            # Extract message content
            clean_message = self._extract_message_content(message)

            # Create dashboard event
            event = DashboardEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_type=event_type,
                conversation_id=conversation_id,
                channel=channel,
                profile_id=profile_id,
                message=clean_message,
                metadata={
                    "level": record.levelname,
                    "logger": record.name,
                },
            )

            # Push to queue
            self._push_event(event)

        except Exception:
            # Silently ignore errors to avoid breaking core functionality
            pass

    def _determine_event_type(self, message: str, level: str) -> Optional[str]:
        """Determine event type from log message."""
        if level == "ERROR":
            return "error"

        for pattern, event_type in EVENT_PATTERNS.items():
            if pattern in message:
                return event_type

        return None

    def _extract_message_content(self, message: str) -> str:
        """Extract clean content from log message."""
        # Remove separator lines
        message = message.replace("=" * 80, "").strip()

        # Extract content after | separator
        if " | " in message:
            parts = message.split(" | ", 1)
            if len(parts) > 1:
                return parts[1].strip()

        # Try to extract content within quotes
        quote_match = re.search(r'"([^"]+)"', message)
        if quote_match:
            return quote_match.group(1)

        return message

    def _push_event(self, event: DashboardEvent) -> None:
        """Push event to queue in thread-safe manner."""
        global _event_queue

        if _event_queue is None:
            return

        with _queue_lock:
            _event_queue.append(event)


def push_sms_event(
    conversation_id: str,
    from_number: str,
    sms_body: str,
    media_urls: Optional[list[dict[str, str]]] = None,
    profile_id: Optional[str] = None,
) -> None:
    """Push an enhanced SMS event with message body and media attachments.

    This is called directly from the server when processing SMS webhooks,
    providing richer data than what the log handler can capture.

    Args:
        conversation_id: The Maestro conversation ID
        from_number: The sender's phone number
        sms_body: The SMS message text
        media_urls: Optional list of media attachment dicts with url, content_type, filename
        profile_id: Optional customer profile ID
    """
    global _event_queue

    if _event_queue is None:
        return

    attachments = []
    if media_urls:
        for i, media in enumerate(media_urls):
            attachments.append(
                MediaAttachment(
                    url=media.get("url", ""),
                    content_type=media.get("content_type", "image/jpeg"),
                    filename=media.get("filename", f"image_{i + 1}"),
                    index=i,
                )
            )

    has_media = len(attachments) > 0
    event_type = "sms_with_media" if has_media else "sms_received"

    # Build descriptive message
    if has_media and sms_body:
        message = f"SMS with {len(attachments)} image(s): {sms_body}"
    elif has_media:
        message = f"SMS with {len(attachments)} image(s)"
    elif sms_body:
        message = f"SMS: {sms_body}"
    else:
        message = "SMS received (empty)"

    event = DashboardEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type=event_type,
        conversation_id=conversation_id,
        channel="sms",
        profile_id=profile_id,
        message=message,
        metadata={"from_number": from_number, "media_count": len(attachments)},
        sms_body=sms_body,
        media_attachments=attachments,
        from_number=from_number,
    )

    with _queue_lock:
        _event_queue.append(event)


def push_voice_transcript(
    conversation_id: str,
    speaker: str,
    text: str,
    profile_id: Optional[str] = None,
) -> None:
    """Push a voice transcript event to the dashboard for real-time display.

    Args:
        conversation_id: The Maestro conversation ID
        speaker: Who is speaking ('customer' or 'agent')
        text: The transcript text
        profile_id: Optional customer profile ID
    """
    global _event_queue

    if _event_queue is None:
        return

    event = DashboardEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type="voice_transcript",
        conversation_id=conversation_id,
        channel="voice",
        profile_id=profile_id,
        message=text,
        metadata={"speaker": speaker},
    )

    with _queue_lock:
        _event_queue.append(event)


def push_demo_status(status: str, message: str, progress: int = 0) -> None:
    """Push a demo status event to the dashboard.

    Args:
        status: Status type ('started', 'progress', 'completed', 'error')
        message: Status message
        progress: Progress percentage (0-100)
    """
    global _event_queue

    if _event_queue is None:
        return

    event = DashboardEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type="demo_status",
        message=message,
        metadata={"status": status, "progress": progress},
    )

    with _queue_lock:
        _event_queue.append(event)


def push_anchor_event(anchor_id: str, anchor_name: str) -> None:
    """Push an anchor selection event to the dashboard."""
    global _event_queue

    if _event_queue is None:
        return

    event = DashboardEvent(
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_type="anchor_selected",
        message=f"Switched to {anchor_name} ({anchor_id})",
        metadata={"anchor_id": anchor_id, "anchor_name": anchor_name},
    )

    with _queue_lock:
        _event_queue.append(event)


def get_event_queue() -> deque:
    """Get the global event queue."""
    global _event_queue

    if _event_queue is None:
        with _queue_lock:
            if _event_queue is None:
                _event_queue = deque(maxlen=MAX_EVENTS)

    return _event_queue


def setup_dashboard_logging() -> None:
    """Set up dashboard logging by attaching custom handler to TAC logger."""
    global _event_queue

    # Initialize event queue
    with _queue_lock:
        _event_queue = deque(maxlen=MAX_EVENTS)

    # Attach dashboard handler to the 'tac' logger
    handler = DashboardLogHandler()
    tac_logger = logging.getLogger("tac")
    tac_logger.addHandler(handler)

    # Also capture anchor-specific logs
    anchor_logger = logging.getLogger("anchors")
    anchor_logger.addHandler(handler)
