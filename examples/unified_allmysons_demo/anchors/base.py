"""Base anchor class defining the interface for all anchor scenarios."""

from __future__ import annotations

import logging
from typing import Any, Optional

from tac import TAC
from tac.channels import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = logging.getLogger(__name__)


class BaseAnchor:
    """Base class for anchor scenario implementations.

    Each anchor defines a specific demo scenario with its own
    message handling logic, system prompt, and scenario metadata.
    """

    # Subclasses must set these
    anchor_id: str = ""
    name: str = ""
    short_description: str = ""
    company_name: str = "All My Sons Moving & Storage"
    scenario_title: str = ""
    scenario_steps: list[dict[str, str]] = []
    channels: list[str] = ["voice", "sms"]

    def __init__(
        self,
        tac: TAC,
        sms_channel: SMSChannel,
        voice_channel: VoiceChannel,
    ) -> None:
        self.tac = tac
        self.sms_channel = sms_channel
        self.voice_channel = voice_channel
        self.conversation_messages: dict[str, list[dict[str, Any]]] = {}
        self.active_voice_calls: dict[str, bool] = {}
        self.phone_to_conversation: dict[str, str] = {}

    def link_phone_to_conversation(self, phone: str, conversation_id: str) -> None:
        """Link a phone number to a conversation for cross-channel routing."""
        self.phone_to_conversation[phone] = conversation_id
        logger.info(
            f"CROSS-CHANNEL | Linked {phone} to conversation {conversation_id[:20]}...",
            extra={"conversation_id": conversation_id},
        )

    def get_conversation_for_phone(self, phone: str) -> Optional[str]:
        """Get the active conversation ID for a phone number."""
        return self.phone_to_conversation.get(phone)

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle an incoming message. Subclasses should override this."""
        raise NotImplementedError("Subclasses must implement handle_message")

    def get_scenario_info(self) -> dict[str, Any]:
        """Return scenario metadata for the dashboard."""
        return {
            "anchor_id": self.anchor_id,
            "name": self.name,
            "short_description": self.short_description,
            "company_name": self.company_name,
            "scenario_title": self.scenario_title,
            "scenario_steps": self.scenario_steps,
            "channels": self.channels,
        }
