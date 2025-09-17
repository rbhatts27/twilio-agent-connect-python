"""Pydantic models for Twilio webhook events."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class WebhookEventType(str, Enum):
    """Enum for Twilio webhook event types."""

    ONMESSAGEADDED = "onMessageAdded"


class TwilioWebhookEvent(BaseModel):
    """
    Main webhook request model from Twilio.
    """

    EventType: str = Field(..., description="Type of webhook event")
    ConversationSid: str = Field(..., description="Conversation SID")
    Body: Optional[str] = Field(None, description="Message body")
    Author: Optional[str] = Field(None, description="Message author")

    def is_message_event(self) -> bool:
        """
        Check if this is a message-related webhook event.

        Returns:
            True if this is a message event, False otherwise
        """
        return self.EventType == "onMessageAdded"

    def should_process_with_agent(self) -> bool:
        """
        Determine if this webhook should be processed by the AI agent.

        Returns:
            True if should be processed by agent, False otherwise
        """
        return (
            self.is_message_event()
            and self.Body is not None
            and self.Body.strip() != ""
        )

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "EventType": "onMessageAdded",
                "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "Author": "+12162622233",
                "Body": "Hello oh",
            }
        }
