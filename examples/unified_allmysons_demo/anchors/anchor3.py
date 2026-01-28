"""
Anchor 3: Seamless Channel Switching

Demo scenario: Customer starts on voice, switches to SMS mid-conversation
(e.g., enters a meeting), then resumes on voice later. The AI maintains
full context across channel transitions.
"""

import logging
from typing import Optional

from anchors.base import BaseAnchor

from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor3ChannelSwitching(BaseAnchor):
    """Anchor 3: Seamless Channel Switching (Stub)."""

    anchor_id = "anchor3"
    name = "Seamless Channel Switching"
    short_description = "Customer moves between voice and SMS without losing context"
    scenario_title = "The Busy Professional"
    scenario_steps = [
        {"number": "1", "text": "Customer calls to discuss moving options (Voice)"},
        {"number": "2", "text": "Customer needs to step into a meeting"},
        {"number": "3", "text": "AI suggests continuing via SMS"},
        {"number": "4", "text": "Conversation continues seamlessly over SMS"},
        {"number": "5", "text": "Customer calls back later, AI picks up where SMS left off"},
    ]

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages with channel switching awareness."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        logger.info(
            f"[ANCHOR3-STUB] Message received on {channel}: {user_message[:50]}",
            conversation_id=conv_id,
            channel=channel,
        )

        response = (
            "Anchor 3 (Seamless Channel Switching) is not yet implemented. "
            "This anchor will demonstrate how customers can switch between "
            "voice and SMS mid-conversation without losing context."
        )

        if channel == "voice":
            await self.voice_channel.send_response(conv_id, response, role="assistant")
        elif channel == "sms":
            await self.sms_channel.send_response(conv_id, response, role="assistant")
