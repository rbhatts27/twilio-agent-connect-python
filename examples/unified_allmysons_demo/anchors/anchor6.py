"""
Anchor 6: Multi-Party Conversation

Demo scenario: Multiple family members interact with the AI about the
same move. The AI tracks who is speaking, maintains shared context,
and coordinates between participants.
"""

import logging
from typing import Optional

from anchors.base import BaseAnchor

from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor6MultiParty(BaseAnchor):
    """Anchor 6: Multi-Party Conversation (Stub)."""

    anchor_id = "anchor6"
    name = "Multi-Party Conversation"
    short_description = "Multiple participants interact with AI about the same move"
    scenario_title = "The Family Move Coordination"
    scenario_steps = [
        {"number": "1", "text": "Maria calls to start the quote process (Voice)"},
        {"number": "2", "text": "Maria's husband Carlos texts inventory photos (SMS)"},
        {"number": "3", "text": "AI recognizes both as same household"},
        {"number": "4", "text": "AI consolidates information from both parties"},
        {"number": "5", "text": "Maria confirms final quote on voice call"},
    ]

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages for multi-party scenario."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        logger.info(
            f"[ANCHOR6-STUB] Message received on {channel}: {user_message[:50]}",
            conversation_id=conv_id,
            channel=channel,
        )

        response = (
            "Anchor 6 (Multi-Party Conversation) is not yet implemented. "
            "This anchor will demonstrate how AI coordinates between multiple "
            "family members interacting about the same move."
        )

        if channel == "voice":
            await self.voice_channel.send_response(conv_id, response, role="assistant")
        elif channel == "sms":
            await self.sms_channel.send_response(conv_id, response, role="assistant")
