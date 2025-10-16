"""SMS Channel implementation for TAF."""

from typing import Any, Optional

from taf import TAF
from taf.channels.base import BaseChannel
from taf.models.conversation_event import ConversationEvent


class SMSChannel(BaseChannel):
    """
    SMS Channel for handling SMS-based conversations.

    Inherits conversation lifecycle management from BaseChannel and provides
    SMS-specific metadata extraction.
    """

    def __init__(self, taf: TAF):
        """
        Initialize SMS channel.

        Args:
            taf: TAF instance for memory/context operations
        """
        super().__init__(taf)

    def process_webhook(self, webhook_data: dict[str, Any]) -> None:
        """
        Process SMS webhook event and manage conversation lifecycle.

        Handles:
        - onConversationAdded: Initialize new conversation
        - onMessageAdded: Process message with existing conversation context
        - onConversationRemoved: Clean up conversation state

        Args:
            webhook_data: Raw webhook event data from Twilio
        """
        try:
            event = ConversationEvent(**webhook_data)
        except Exception as e:
            self.logger.error(f"Failed to parse webhook event: {e}")
            return

        conv_id = event.conversation_id
        if not conv_id:
            self.logger.error("No conversation_id in webhook event")
            return

        # Handle conversation lifecycle events
        # TODO: Check event_type based on actual webhook data
        if event.event_type == "onConversationAdded":
            self._handle_conversation_started(conv_id, event)
        elif event.event_type == "onMessageAdded":
            self._handle_message(conv_id, event)
        elif event.event_type == "onConversationRemoved":
            self._end_conversation(conv_id)
        else:
            self.logger.debug(f"Ignoring event type: {event.event_type}")

    async def send_response(
        self, conversation_id: str, response: str, role: Optional[str] = None
    ) -> None:
        """
        Send SMS response for a conversation.

        Args:
            conversation_id: Conversation ID to send response to
            response: Message content to send
            role: Optional message role (not used in SMS channel)

        Note:
            This is a placeholder implementation. In production, this would
            use the Twilio SMS API to send the actual message.
        """
        if conversation_id not in self._conversations:
            self.logger.error(f"Cannot send response: conversation {conversation_id} not found")
            return

        session = self._conversations[conversation_id]

        # TODO: Implement actual SMS sending via Twilio API
        self.logger.info(f"[SMS] Sending response to conversation {conversation_id}: {response}")
        self.logger.debug(f"Profile: {session.profile_id}")

    def get_channel_name(self) -> str:
        """Get the channel name identifier."""
        return "sms"

    def _handle_conversation_started(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle conversation started event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Extract profile_id from event
        profile_id = event.participant_profile_id

        if not profile_id:
            self.logger.error(f"No profile_id found in onConversationAdded event for {conv_id}")
            return

        self._start_conversation(conv_id, profile_id)

    def _handle_message(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle incoming message event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Validate message has content
        message_body = event.communication_message_body
        if not message_body or not message_body.strip():
            self.logger.debug(f"Empty message in conversation {conv_id}, ignoring")
            return

        # Auto-initialize conversation if not already started
        if conv_id not in self._conversations:
            profile_id = event.participant_profile_id
            if not profile_id:
                self.logger.error(
                    f"No profile_id found for conversation {conv_id}, cannot process message"
                )
                return
            self._start_conversation(conv_id, profile_id)

        session = self._conversations[conv_id]

        # Retrieve memory and trigger callback using the session
        self.taf.retrieve_memory(session, query=message_body)
