"""Base channel interface for TAF channels."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from taf import TAF
from taf.core.context import ConversationSession
from taf.core.logging import get_logger


class BaseChannel(ABC):
    """
    Abstract base class for TAF channels.

    Channels handle protocol-specific webhook processing and response delivery
    for different communication channels (SMS, Voice, etc.).

    This class provides common conversation lifecycle management that is shared
    across all channel types.
    """

    def __init__(self, taf: TAF):
        """
        Initialize base channel.

        Args:
            taf: TAF instance for memory/context operations
        """
        self.taf = taf
        self.logger = get_logger(__name__)

        # Track active conversations (shared across all channel types)
        self._conversations: Dict[str, ConversationSession] = {}

    @abstractmethod
    def process_webhook(self, webhook_data: Dict[str, Any]) -> None:
        """
        Process incoming webhook event from Twilio.

        This method should:
        1. Parse and validate webhook data
        2. Handle conversation lifecycle (start, message, end)
        3. Trigger memory retrieval via TAF
        4. Invoke registered callbacks

        Args:
            webhook_data: Raw webhook event data from Twilio
        """
        pass

    @abstractmethod
    def send_response(self, conversation_id: str, response: str) -> None:
        """
        Send response back through the channel.

        Args:
            conversation_id: Conversation ID to send response to
            response: Message content to send
        """
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """
        Get the channel name identifier.

        Returns:
            Channel name (e.g., 'sms', 'voice')
        """
        pass

    def _start_conversation(self, conv_id: str, profile_id: str) -> None:
        """
        Initialize new conversation session.

        Args:
            conv_id: Conversation ID
            profile_id: Profile ID for the conversation
        """
        if conv_id in self._conversations:
            self.logger.warning(
                f"Conversation {conv_id} already exists, skipping initialization"
            )
            return

        # Store conversation session
        self._conversations[conv_id] = ConversationSession(
            conversation_id=conv_id,
            profile_id=profile_id,
            channel=self.get_channel_name(),
        )

        self.logger.info(f"Started conversation {conv_id} for profile {profile_id}")

    def _end_conversation(self, conv_id: str) -> None:
        """
        Clean up conversation session.

        Args:
            conv_id: Conversation ID
        """
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            self.logger.info(f"Ended conversation {conv_id}")
        else:
            self.logger.warning(f"Attempted to end unknown conversation {conv_id}")
