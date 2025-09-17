"""Core TAF (Twilio Agentic Framework) class for processing events and configuration."""

from typing import Any, Dict, Optional, Union

from pydantic import ValidationError

from ..models.config import TAFConfig
from ..models.webhook import TwilioWebhookEvent


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

    def process_message(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a Twilio webhook message event.

        Args:
            event_data: Dictionary containing Twilio webhook event data

        Returns:
            Dict[str, Any]: Processing result with event info and decision

        Raises:
            ValueError: If event_data cannot be parsed as TwilioWebhookEvent
        """
        # Parse and validate the webhook event
        try:
            event = TwilioWebhookEvent(**event_data)
        except ValidationError as e:
            raise ValueError(f"Invalid webhook event data: {e}") from e

        # Analyze the event
        should_process = event.should_process_with_agent()

        return {
            "event": {
                "type": event.EventType,
                "conversation_sid": event.ConversationSid,
                "body": event.Body,
                "author": event.Author,
                "is_message_event": event.is_message_event(),
            },
            "processing": {
                "should_process": should_process,
                "model_provider": self.config.model_provider,
            },
            "config": self.config.dict(),
        }

    def get_model_provider(self) -> str:
        """
        Get the configured AI model provider.

        Returns:
            str: Model provider name
        """
        return self.config.model_provider

    def __repr__(self) -> str:
        """String representation of TAF instance."""
        return f"TAF(model_provider={self.config.model_provider})"
