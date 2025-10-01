"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

from typing import Any, Dict, List, Optional, Union

from pydantic import ValidationError

from ..context.maestro import MaestroClient
from ..context.memora import MemoraClient
from ..models.webhook import TwilioWebhookEvent
from .config import TAFConfig
from .context import SessionIdentity
from .logging import get_logger, setup_logging


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

        # Setup logging
        setup_logging(log_level=self.config.log_level)
        self.logger = get_logger(__name__)

        self.memora_client = MemoraClient(
            base_url=self.config.memora_base_url,
            auth_token=self.config.twilio_auth_token,
        )
        self.maestro_client = MaestroClient(
            base_url=self.config.maestro_base_url,
            account_sid=self.config.twilio_account_sid,
        )

    def resolve_identity(
        self, event_data: Dict[str, Any], profile_id: Optional[str]
    ) -> SessionIdentity:
        """
        Process a Twilio webhook message event, return identity if valid.

        Args:
            event_data: Dictionary containing Twilio webhook event data
            profile_id: Profile ID to associate with the conversation

        Returns:
            SessionIdentity: Identity information for the session

        Raises:
            ValueError: If event_data cannot be parsed as a valid webhook event or profile_id is None
        """
        if profile_id is None:
            self.logger.error("Profile ID is required but was None")
            raise ValueError("profile_id is required")

        try:
            conversation = self.maestro_client.create_conversation()

            participant = self.maestro_client.add_participant(
                conversation_id=conversation.id, profile_id=profile_id
            )

            return SessionIdentity(
                profile_id=participant.profile_id, conversation_id=conversation.id
            )
        except Exception as e:
            self.logger.error(f"Failed to resolve identity: {e}")
            raise

    def build_context(
        self, service_id: str, identity: SessionIdentity, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch context from Memora.

        Args:
            service_id: Memora service ID
            identity: Session identity containing profile and conversation information
            query: Optional query string for context retrieval

        Returns:
            List of memory dictionaries from Memora
        """
        try:
            context = self.memora_client.retrieve_context(
                service_id=service_id,
                profile_id=identity.profile_id,
                query=query,
            )
            context_count = len(context) if isinstance(context, list) else "N/A"
            return context
        except Exception as e:
            self.logger.error(f"Failed to build context: {e}")
            raise

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
