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
    MessagingServiceSid: Optional[str] = Field(
        None, description="Messaging Service SID"
    )
    Attributes: Optional[str] = Field(None, description="Event attributes")
    DateCreated: Optional[str] = Field(None, description="Event creation date")
    Index: Optional[str] = Field(None, description="Message index")
    ChatServiceSid: Optional[str] = Field(None, description="Chat Service SID")
    MessageSid: Optional[str] = Field(None, description="Message SID")
    AccountSid: Optional[str] = Field(None, description="Account SID")
    Source: Optional[str] = Field(None, description="Message source")
    RetryCount: Optional[str] = Field(None, description="Retry count")
    ParticipantSid: Optional[str] = Field(None, description="Participant SID")

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
                "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
                "Author": "+12162622233",
                "Body": "Teaching",
                "MessagingServiceSid": "MG3675a614bcfcfb1921727b0138617cdf",
                "MessageSid": "IMf570e4a1af7c4d8381c9454bd7fbdf9b",
                "AccountSid": "ACa0cec02523bd4da792b4bff42b77fc22",
                "Source": "SMS",
                "ParticipantSid": "MB723da60623f74438acee5baafbd438f0",
                "ChatServiceSid": "IS21622ffdbc4947a4a0c1abaa77dfd024",
            }
        }
