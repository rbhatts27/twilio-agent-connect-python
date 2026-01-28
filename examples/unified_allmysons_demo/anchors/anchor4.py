"""
Anchor 4: AI-to-Human Transfer

Demo scenario: AI handles initial inquiry, detects a complex situation
(e.g., international move with customs), and smoothly transfers to a
human specialist while preserving full conversation context.
"""

from typing import Optional

from anchors.base import BaseAnchor

from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor4HumanTransfer(BaseAnchor):
    """Anchor 4: AI-to-Human Transfer (Stub)."""

    anchor_id = "anchor4"
    name = "AI-to-Human Transfer"
    short_description = "AI detects complexity and transfers to human with full context"
    scenario_title = "The International Move"
    scenario_steps = [
        {"number": "1", "text": "Customer calls about an international move"},
        {"number": "2", "text": "AI gathers basic details and detects complexity"},
        {"number": "3", "text": "AI explains it will transfer to a specialist"},
        {"number": "4", "text": "Handoff to human agent via Flex with full context"},
        {"number": "5", "text": "Human agent sees complete conversation history"},
    ]

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages with human transfer awareness."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        logger.info(
            f"[ANCHOR4-STUB] Message received on {channel}: {user_message[:50]}",
            conversation_id=conv_id,
            channel=channel,
        )

        response = (
            "Anchor 4 (AI-to-Human Transfer) is not yet implemented. "
            "This anchor will demonstrate how the AI detects complex situations "
            "and transfers to a human agent via Flex with full context preserved."
        )

        if channel == "voice":
            await self.voice_channel.send_response(conv_id, response, role="assistant")
        elif channel == "sms":
            await self.sms_channel.send_response(conv_id, response, role="assistant")
