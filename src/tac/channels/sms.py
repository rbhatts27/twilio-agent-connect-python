"""SMS Channel implementation for TAC."""

from typing import Any, Optional

from twilio.rest import Client

from tac import TAC
from tac.channels.base import BaseChannel

# TODO: Use Vnext Conversation Event when it is ready
from tac.models.conversation import (
    CommunicationContent,
    CommunicationParticipant,
    CommunicationRequest,
)
from tac.models.conversation_event import ConversationEvent, ConversationEventType
from tac.models.session import AuthorInfo


class SMSChannel(BaseChannel):
    """
    SMS Channel for handling SMS-based conversations.

    Inherits conversation lifecycle management from BaseChannel and provides
    SMS-specific metadata extraction.
    """

    def __init__(self, tac: TAC):
        """
        Initialize SMS channel.

        Args:
            tac: TAC instance for memory/context operations
        """
        super().__init__(tac)
        self.twilio = Client(tac.config.twilio_account_sid, tac.config.twilio_auth_token)

    async def process_webhook(self, webhook_data: dict[str, Any]) -> None:
        """
        Process SMS webhook event and manage conversation lifecycle.

        Handles:
        - conversation.created: Initialize new conversation
        - participant.added: Track profile_id when customer joins
        - communication.created: Process incoming messages from customers
        - conversation.updated: Clean up when conversation is closed

        Args:
            webhook_data: Raw webhook event data from Twilio
        """
        try:
            event = ConversationEvent(**webhook_data)
        except Exception as e:
            self.logger.error("Failed to parse webhook event", error=str(e), exc_info=True)
            return

        conv_id = event.conversation_id
        if not conv_id:
            self.logger.error("No conversation_id in webhook event")
            return

        if event.author_channel and event.author_channel != "SMS":
            self.logger.debug(
                "Ignoring non-SMS event",
                conversation_id=conv_id,
                channel=event.author_channel,
            )
            return

        # Handle conversation lifecycle events
        if event.event_type == ConversationEventType.CONVERSATION_CREATED:
            await self._handle_conversation_created(conv_id, event)
        elif event.event_type == ConversationEventType.PARTICIPANT_ADDED:
            await self._handle_participant_added(conv_id, event)
        elif event.event_type == ConversationEventType.COMMUNICATION_CREATED:
            await self._handle_communication_created(conv_id, event)
        elif event.event_type == ConversationEventType.CONVERSATION_UPDATED:
            self._handle_conversation_updated(conv_id, event)
        else:
            self.logger.debug(
                "Ignoring event type",
                conversation_id=conv_id,
                event_type=event.event_type,
            )

    async def send_response(
        self, conversation_id: str, response: str, role: Optional[str] = None
    ) -> None:
        """
        Send SMS response for a conversation using the Maestro Communications API.

        Args:
            conversation_id: Conversation ID to send response to
            response: Message content to send
            role: Optional message role (not used in SMS channel)

        Note:
            This is a placeholder implementation. In production, this would
            use the Twilio SMS API to send the actual message.
        """
        if conversation_id not in self._conversations:
            self.logger.error(
                "Cannot send response: conversation not found",
                conversation_id=conversation_id,
            )
            return

        self.logger.info(
            "Sending SMS response via Twilio",
            conversation_id=conversation_id,
        )

        # TODO this is a super hacky workaround because Maestro isn't ready to
        # support sending messages yet. Defensively go from conversation_id ->
        # participant -> address -> phone number
        try:
            participants = await self.tac.maestro_client.list_participants(conversation_id)
        except Exception as e:
            self.logger.error(
                "Failed to list participants",
                conversation_id=conversation_id,
                error=str(e),
            )
            self.logger.info("Continuing without sending response via Maestro")
            return

        for participant in participants:
            if participant.type != "CUSTOMER":
                self.logger.debug("Found non-customer participant; skipping")
                continue

            for address in participant.addresses:
                if address.channel != "SMS":
                    self.logger.debug("Found non-SMS address; skipping")
                    continue

                self.logger.debug(
                    "Sending SMS response",
                    conversation_id=conversation_id,
                    to_address=address.address,
                )
                self.twilio.messages.create(
                    to=address.address,
                    from_=self.tac.config.twilio_phone_number,
                    body=response,
                )
                self.logger.info(
                    "Sent SMS response",
                    conversation_id=conversation_id,
                    to_address=address.address,
                )

    def get_channel_name(self) -> str:
        """Get the channel name identifier."""
        return "sms"

    async def _handle_conversation_created(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle conversation.created event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        self.logger.debug("Conversation created", conversation_id=conv_id)
        # Start conversation without profile_id initially
        # Profile ID will be added when participant.added event arrives
        await self._start_conversation(conv_id, profile_id=None)

    async def _handle_participant_added(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle participant.added event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Only track CUSTOMER participants with profile_id
        if event.participant_type == "CUSTOMER" and event.profile_id:
            self.logger.debug(
                "Customer participant added",
                conversation_id=conv_id,
                profile_id=event.profile_id,
            )

            # Auto-initialize conversation if not already started
            if conv_id not in self._conversations:
                await self._start_conversation(conv_id, event.profile_id)
            else:
                # Update existing conversation with profile_id
                session = self._conversations[conv_id]
                session.profile_id = event.profile_id

                # Fetch profile immediately
                if self.tac.is_twilio_memory_enabled():
                    profile = await self.tac.fetch_profile(event.profile_id)
                    if profile:
                        session.profile = profile
        else:
            self.logger.debug(
                "Participant added",
                conversation_id=conv_id,
                participant_type=event.participant_type,
                profile_id=event.profile_id,
            )

    async def _handle_communication_created(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle communication.created event (incoming message).

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # TODO: Figure out a way to filter out messages from non-CUSTOMER participants
        if event.author_address == self.tac.config.twilio_phone_number:
            self.logger.debug(
                "Ignoring message from AI agent",
                conversation_id=conv_id,
            )
            return
        # Extract message text from body (maybe JSON)
        message_text = event.get_message_text()
        if not message_text or not message_text.strip():
            self.logger.debug(
                "Empty message, ignoring",
                conversation_id=conv_id,
            )
            return

        # Only process messages from CUSTOMER participants
        # Check if author is a customer by looking up the participant
        if conv_id not in self._conversations:
            self.logger.debug(
                "Received message for unknown conversation, auto-initializing without profile",
                conversation_id=conv_id,
            )
            await self._start_conversation(conv_id, profile_id=None)

        session = self._conversations[conv_id]

        # Update session with author info from the communication event
        if event.author_address and event.author_participant_id:
            session.author_info = AuthorInfo(
                address=event.author_address,
                participant_id=event.author_participant_id,
            )

        # Fetch profile for each message if profile_id is available
        if session.profile_id and self.tac.is_twilio_memory_enabled():
            profile = await self.tac.fetch_profile(session.profile_id)
            if profile:
                # Update session with fresh profile data
                session.profile = profile

        # Retrieve memory only if Twilio Memory is enabled
        memory_response = None
        if self.tac.is_twilio_memory_enabled():
            try:
                memory_response = await self.tac.retrieve_memory(session, query=message_text)
                self.logger.debug(
                    "Memory retrieved",
                    conversation_id=conv_id,
                )
            except Exception as e:
                self.logger.error(
                    "Failed to retrieve memory",
                    conversation_id=conv_id,
                    error=str(e),
                    exc_info=True,
                )
                # Continue without memory rather than failing the entire message processing
        else:
            self.logger.debug(
                "Twilio Memory not enabled, skipping memory retrieval",
                conversation_id=conv_id,
            )

        # Trigger message ready callback (with or without memory)
        try:
            await self.tac.trigger_message_ready(message_text, session, memory_response)
        except Exception as e:
            self.logger.error(
                "Error in message ready callback",
                conversation_id=conv_id,
                error=str(e),
                exc_info=True,
            )

    def _handle_conversation_updated(self, conv_id: str, event: ConversationEvent) -> None:
        """
        Handle conversation.updated event.

        Args:
            conv_id: Conversation ID
            event: Parsed conversation event
        """
        # Check if conversation is closed
        if event.conversation_status == "CLOSED":
            self.logger.debug(
                "Conversation closed, cleaning up",
                conversation_id=conv_id,
            )
            self._end_conversation(conv_id)
        else:
            self.logger.debug(
                "Conversation updated",
                conversation_id=conv_id,
                status=event.conversation_status,
            )

    async def _send_response_via_maestro(self, conversation_id: str, response: str) -> None:
        """
        Send SMS response via Maestro Communications API. This is only for demo purpose.

        TODO: Remove this before going production.

        Args:
            conversation_id: Conversation ID to send response to
            response: Message content to send
        """
        session = self._conversations[conversation_id]

        # Build recipient from author_info in session
        if not session.author_info:
            self.logger.error(
                "Cannot send response: no author_info",
                conversation_id=conversation_id,
            )
            return

        recipient = CommunicationParticipant(
            address=session.author_info.address,
            channel="SMS",
            participantId=session.author_info.participant_id,
        )
        recipients = [recipient]

        # Create author using AI_AGENT type and configured Twilio phone number
        # Note: We don't need to find an actual AI_AGENT participant,
        # we can create the author directly
        author = CommunicationParticipant(
            address=self.tac.config.twilio_phone_number,
            channel="SMS",
            participantId=None,  # No participant ID needed for AI agent
        )
        content = CommunicationContent(type="TEXT", text=response)
        comm_request = CommunicationRequest(author=author, content=content, recipients=recipients)

        # Send communication via Maestro
        try:
            self.logger.debug(
                "Sending communication via Maestro",
                conversation_id=conversation_id,
            )
            await self.tac.maestro_client.add_communication(conversation_id, comm_request)
            self.logger.info(
                "Sent response via Maestro",
                conversation_id=conversation_id,
            )
        except Exception as e:
            self.logger.error(
                "Failed to send communication",
                conversation_id=conversation_id,
                error=str(e),
                exc_info=True,
            )
