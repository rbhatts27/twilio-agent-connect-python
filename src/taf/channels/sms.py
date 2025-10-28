"""SMS Channel implementation for TAF."""

from typing import Any, Optional

from twilio.rest import Client

from taf import TAF
from taf.channels.base import BaseChannel

# TODO: Use Vnext Conversation Event when it is ready
from taf.models.conversation_event import TwilioConversationEvent


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
        self.twilio = Client(taf.config.twilio_account_sid, taf.config.twilio_auth_token)

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
            event = TwilioConversationEvent(**webhook_data)
        except Exception as e:
            self.logger.error(f"Failed to parse webhook event: {e}")
            return

        conv_id = event.conversation_sid
        if not conv_id:
            self.logger.error("No conversation_sid in webhook event")
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

        self.logger.info(f"[SMS] Sending response to conversation {conversation_id}: {response}")
        self.twilio.conversations.v1.conversations(conversation_id).messages.create(
            body=response, author=role
        )

    def get_channel_name(self) -> str:
        """Get the channel name identifier."""
        return "sms"

    def _handle_conversation_started(self, conv_id: str, event: TwilioConversationEvent) -> None:
        """
        Handle conversation started event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Extract profile_id from event
        profile_id = event.profile_id
        self.twilio.conversations.v1.conversations(conv_id).participants.create(
            messaging_binding_address=event.author,
        )
        self._start_conversation(conv_id, profile_id)

    def _handle_message(self, conv_id: str, event: TwilioConversationEvent) -> None:
        """
        Handle incoming message event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Validate message has content
        message_body = event.body
        if not message_body or not message_body.strip():
            self.logger.debug(f"Empty message in conversation {conv_id}, ignoring")
            return

        # Auto-initialize conversation if not already started
        if conv_id not in self._conversations:
            profile_id = event.profile_id
            self._start_conversation(conv_id, profile_id)

        session = self._conversations[conv_id]

        # Retrieve memory and trigger callback using the session
        self.taf.retrieve_memory(session, query=message_body)
