"""SMS Channel implementation for TAF."""

from typing import Any, Dict

from taf import TAF
from taf.channels.base import BaseChannel
from taf.core.context import ConversationContext
from taf.models.webhook import TwilioWebhookEvent


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

    def process_webhook(self, webhook_data: Dict[str, Any]) -> None:
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
            event = TwilioWebhookEvent(**webhook_data)
        except Exception as e:
            self.logger.error(f"Failed to parse webhook event: {e}")
            return

        conv_id = event.ConversationSid

        # Handle conversation lifecycle events
        if event.EventType == "onConversationAdded":
            self._handle_conversation_started(conv_id, webhook_data)
        elif event.EventType == "onMessageAdded":
            self._handle_message(conv_id, event, webhook_data)
        elif event.EventType == "onConversationRemoved":
            self._end_conversation(conv_id)
        else:
            self.logger.debug(f"Ignoring event type: {event.EventType}")

    def send_response(self, conversation_id: str, response: str) -> None:
        """
        Send SMS response for a conversation.

        Args:
            conversation_id: Conversation ID to send response to
            response: Message content to send

        Note:
            This is a placeholder implementation. In production, this would
            use the Twilio SMS API to send the actual message.
        """
        if conversation_id not in self._conversations:
            self.logger.error(
                f"Cannot send response: conversation {conversation_id} not found"
            )
            return

        session = self._conversations[conversation_id]

        # TODO: Implement actual SMS sending via Twilio API
        self.logger.info(
            f"[SMS] Sending response to conversation {conversation_id}: {response}"
        )
        self.logger.debug(f"Profile: {session.profile_id}")

    def get_channel_name(self) -> str:
        """Get the channel name identifier."""
        return "sms"

    def _handle_conversation_started(
        self, conv_id: str, webhook_data: Dict[str, Any]
    ) -> None:
        """
        Handle conversation started event.

        Args:
            conv_id: Conversation ID
            webhook_data: Raw webhook data containing profile_id
        """
        # Extract profile_id from webhook data
        profile_id = webhook_data.get("profile_id") or webhook_data.get("ProfileId")

        if not profile_id:
            self.logger.error(
                f"No profile_id found in onConversationAdded event for {conv_id}"
            )
            return

        self._start_conversation(conv_id, profile_id)

    def _handle_message(
        self, conv_id: str, event: TwilioWebhookEvent, webhook_data: Dict[str, Any]
    ) -> None:
        """
        Handle incoming message event.

        Args:
            conv_id: Conversation ID
            event: Parsed webhook event
            webhook_data: Raw webhook data
        """
        # Validate message has content
        if not event.Body or not event.Body.strip():
            self.logger.debug(f"Empty message in conversation {conv_id}, ignoring")
            return

        # Auto-initialize conversation if not already started
        if conv_id not in self._conversations:
            profile_id = webhook_data.get("profile_id") or webhook_data.get("ProfileId")
            if not profile_id:
                self.logger.error(
                    f"No profile_id found for conversation {conv_id}, cannot process message"
                )
                return
            self._start_conversation(conv_id, profile_id)

        session = self._conversations[conv_id]

        # Create conversation context
        conversation_context = ConversationContext(
            conversation_id=conv_id,
            profile_id=session.profile_id,
            channel=self.get_channel_name(),
        )

        # Retrieve memory and trigger callback
        self.taf.retrieve_memory(conversation_context, query=event.Body)
