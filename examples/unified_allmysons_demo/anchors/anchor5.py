"""
Anchor 5: Proactive Outreach

Demo scenario: AI proactively reaches out to customers based on
triggers (e.g., move date approaching, weather alerts affecting
scheduled moves, follow-up on pending quotes).
"""

from typing import Optional

from anchors.base import BaseAnchor

from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor5ProactiveOutreach(BaseAnchor):
    """Anchor 5: Proactive Outreach (Stub)."""

    anchor_id = "anchor5"
    name = "Proactive Outreach"
    short_description = "AI initiates contact based on triggers and customer context"
    scenario_title = "The Move Day Preparation"
    scenario_steps = [
        {"number": "1", "text": "Move date is 3 days away - trigger fires"},
        {"number": "2", "text": "AI sends SMS with move day checklist"},
        {"number": "3", "text": "Customer responds with questions"},
        {"number": "4", "text": "AI answers using full booking context from memory"},
        {"number": "5", "text": "AI confirms crew details and arrival window"},
    ]

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages for proactive outreach scenario."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        logger.info(
            f"[ANCHOR5-STUB] Message received on {channel}: {user_message[:50]}",
            conversation_id=conv_id,
            channel=channel,
        )

        response = (
            "Anchor 5 (Proactive Outreach) is not yet implemented. "
            "This anchor will demonstrate how AI proactively reaches out to "
            "customers based on triggers like approaching move dates."
        )

        if channel == "voice":
            await self.voice_channel.send_response(conv_id, response, role="assistant")
        elif channel == "sms":
            await self.sms_channel.send_response(conv_id, response, role="assistant")
