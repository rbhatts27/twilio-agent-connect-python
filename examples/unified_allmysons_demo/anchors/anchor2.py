"""
Anchor 2: Context Preservation Across Time

Demo scenario: A returning customer calls back days later. The AI recalls
previous conversations, preferences, and quote details from memory,
providing a seamless continuation of the relationship.
"""

from typing import Optional

from anchors.base import BaseAnchor

from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor2ContextPreservation(BaseAnchor):
    """Anchor 2: Context Preservation Across Time (Stub)."""

    anchor_id = "anchor2"
    name = "Context Preservation"
    short_description = "AI recalls previous conversations and preferences across sessions"
    scenario_title = "The Returning Customer"
    scenario_steps = [
        {"number": "1", "text": "Customer called last week for a quote (history in memory)"},
        {"number": "2", "text": "Customer calls back to finalize details"},
        {"number": "3", "text": "AI recalls previous quote, preferences, special items"},
        {"number": "4", "text": "AI continues conversation seamlessly without re-asking"},
        {"number": "5", "text": "Customer books the move with updated details"},
    ]

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages with context preservation awareness."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        logger.info(
            f"[ANCHOR2-STUB] Message received on {channel}: {user_message[:50]}",
            conversation_id=conv_id,
            channel=channel,
        )

        # Stub response
        response = (
            "Anchor 2 (Context Preservation) is not yet implemented. "
            "This anchor will demonstrate how AI recalls previous conversations "
            "and customer preferences across sessions using Memory."
        )

        if channel == "voice":
            await self.voice_channel.send_response(conv_id, response, role="assistant")
        elif channel == "sms":
            await self.sms_channel.send_response(conv_id, response, role="assistant")
