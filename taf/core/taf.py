"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

from typing import Any, Dict, Optional, Union

from pydantic import ValidationError

from taf.context.maestro import MaestroClient
from taf.context.memora import MemoraClient, MemoraMemory
from taf.core.config import TAFConfig

from ..models.webhook import TwilioWebhookEvent
from .context import Memory, Profile, SessionContext, SessionIdentity


class TAF:
    """
    Main Twilio Agentic Framework class for processing webhook events with configuration.

    This class accepts configuration and provides methods to process webhook events.
    """

    def __init__(self, config: Union[TAFConfig, Dict[str, Any]]):
        """
        Initialize TAF instance with configuration.

        Args:
            config: TAFConfig instance or dictionary with configuration settings

        Raises:
            ValueError: If config is invalid
        """
        # Parse and validate configuration
        if isinstance(config, dict):
            try:
                self.config = TAFConfig(**config)
            except ValidationError as e:
                raise ValueError(f"Invalid configuration: {e}")
        elif isinstance(config, TAFConfig):
            self.config = config
        else:
            raise ValueError("Config must be TAFConfig instance or dictionary")

        self.memora_client = MemoraClient()
        self.maestro_client = MaestroClient()

    def resolve_identity(self, event_data: Dict[str, Any]) -> SessionIdentity:
        """
        Process a Twilio webhook message event, return identity if valid.

        Args:
            event_data: Dictionary containing Twilio webhook event data

        Returns:
            SessionIdentity: Identity information for the session

        Raises:
            ValueError: If event_data cannot be parsed as TwilioWebhookEvent
        """

        # Parse and validate the webhook event
        try:
            event = TwilioWebhookEvent(**event_data)
        except ValidationError as e:
            raise ValueError(f"Invalid webhook event data: {e}") from e

        # TODO: Get profile id from maestro when implemented

        return SessionIdentity(profile_id="", conversation_sid=event.ConversationSid)

    def build_context(self, identity: SessionIdentity) -> SessionContext:
        """
        Fetch context from Memora.

        Args:
            identity: Session identity containing profile and conversation information

        Returns:
            SessionContext: Complete session context with profile and memory
        """
        # Only fetch memory if memora service is configured
        memora_memory = None
        if self.config.memora_service_id and identity.profile_id:
            memora_memory = self.memora_client.retrieve_context(
                service_id=self.config.memora_service_id,
                profile_id=identity.profile_id,
                query=None,
            )

        return SessionContext(
            profile=Profile(id=identity.profile_id),
            memory=Memory(
                conversation_sid=identity.conversation_sid, memory_list=memora_memory
            ),
        )

    def process_message(self, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Process a Twilio webhook message event.

        Args:
            event_data: Dictionary containing Twilio webhook event data

        Returns:
            Optional[str]: Message body content if it's an onMessageAdded event with content,
            or None if event type is not supported or message is empty

        Raises:
            ValueError: If event_data cannot be parsed as TwilioWebhookEvent
        """
        # Parse and validate the webhook event
        try:
            event = TwilioWebhookEvent(**event_data)
        except ValidationError as e:
            raise ValueError(f"Invalid webhook event data: {e}") from e

        # Only process message events with content
        if not event.should_process_with_agent():
            return None

        # Return the message body for now
        return event.Body
