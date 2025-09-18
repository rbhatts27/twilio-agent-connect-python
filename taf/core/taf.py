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
        # Check if this is a supported event type first
        event_type = event_data.get("EventType", "")

        if event_type != "onMessageAdded":
            # Unsupported event type - ignore silently
            print(f"🤖 TAF: ⚠️  Filter (Unsupported event type)")
            return None

        # Parse and validate the webhook event (only for onMessageAdded)
        try:
            event = TwilioWebhookEvent(**event_data)
        except ValidationError as e:
            raise ValueError(f"Invalid webhook event data: {e}") from e

        # Return body content if it has content, otherwise None
        if event.Body is not None and event.Body.strip() != "":
            print(
                f"🤖 TAF: ✅ Process '{event.Body[:30]}{'...' if len(event.Body) > 30 else ''}'"
            )
            return event.Body.strip()
        else:
            print(f"🤖 TAF: ⚠️  Filter (empty message)")
            return None
