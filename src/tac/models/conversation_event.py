"""Models for Twilio Conversation Events."""

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ConversationEventType(str, Enum):
    """Enum for Maestro Conversation Event types."""

    CONVERSATION_CREATED = "CONVERSATION_CREATED"
    CONVERSATION_UPDATED = "CONVERSATION_UPDATED"
    PARTICIPANT_ADDED = "PARTICIPANT_ADDED"
    COMMUNICATION_CREATED = "COMMUNICATION_CREATED"


class ParticipantAddress(BaseModel):
    """Represents a participant's address."""

    channel: Optional[str] = None
    address: Optional[str] = None
    channel_id: Optional[str] = Field(None, alias="channelId")

    model_config = {"populate_by_name": True}


class ConversationConfiguration(BaseModel):
    """Configuration for a conversation."""

    intelligence_service_ids: Optional[list[str]] = Field(None, alias="intelligenceServiceIds")

    model_config = {"populate_by_name": True}


class ConversationData(BaseModel):
    """Data for CONVERSATION_CREATED and CONVERSATION_UPDATED events."""

    id: str
    account_id: str = Field(..., alias="accountId")
    service_id: str = Field(..., alias="serviceId")
    status: str
    name: Optional[str] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    configuration: Optional[ConversationConfiguration] = None

    model_config = {"populate_by_name": True}


class ParticipantData(BaseModel):
    """Data for PARTICIPANT_ADDED events."""

    id: str
    conversation_id: str = Field(..., alias="conversationId")
    account_id: str = Field(..., alias="accountId")
    service_id: str = Field(..., alias="serviceId")
    name: Optional[str] = None
    type: Optional[Literal["HUMAN_AGENT", "CUSTOMER", "AI_AGENT", "UNKNOWN"]] = None
    profile_id: Optional[str] = Field(None, alias="profileId")
    addresses: Optional[list[ParticipantAddress]] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class CommunicationAuthor(BaseModel):
    """Author information for a communication."""

    address: str
    channel: str
    participant_id: str = Field(..., alias="participantId")

    model_config = {"populate_by_name": True}


class CommunicationContent(BaseModel):
    """Content of a communication."""

    type: str
    text: Optional[str] = None

    model_config = {"populate_by_name": True}


class CommunicationRecipient(BaseModel):
    """Represents a recipient of a communication."""

    address: str
    channel: str
    participant_id: str = Field(..., alias="participantId")
    delivery_status: Optional[str] = Field(None, alias="deliveryStatus")

    model_config = {"populate_by_name": True}


class CommunicationData(BaseModel):
    """Data for COMMUNICATION_CREATED events."""

    id: str
    conversation_id: str = Field(..., alias="conversationId")
    account_id: str = Field(..., alias="accountId")
    service_id: str = Field(..., alias="serviceId")
    author: CommunicationAuthor
    content: CommunicationContent
    channel_id: Optional[str] = Field(None, alias="channelId")
    recipients: Optional[list[CommunicationRecipient]] = None
    created_at: Optional[str] = Field(None, alias="createdAt")
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    model_config = {"populate_by_name": True}


class ConversationEvent(BaseModel):
    """Represents a Twilio Conversation Event."""

    event_type: str = Field(..., alias="eventType")
    timestamp: str
    data: dict[str, Any]  # Generic dict to handle all event types

    model_config = {"populate_by_name": True}

    def get_conversation_data(self) -> Optional[ConversationData]:
        """Parse data as ConversationData for CONVERSATION_CREATED/UPDATED events."""
        if self.event_type in [
            ConversationEventType.CONVERSATION_CREATED,
            ConversationEventType.CONVERSATION_UPDATED,
        ]:
            return ConversationData.model_validate(self.data)
        return None

    def get_participant_data(self) -> Optional[ParticipantData]:
        """Parse data as ParticipantData for PARTICIPANT_ADDED events."""
        if self.event_type == ConversationEventType.PARTICIPANT_ADDED:
            return ParticipantData.model_validate(self.data)
        return None

    def get_communication_data(self) -> Optional[CommunicationData]:
        """Parse data as CommunicationData for COMMUNICATION_CREATED events."""
        if self.event_type == ConversationEventType.COMMUNICATION_CREATED:
            return CommunicationData.model_validate(self.data)
        return None

    def get_message_text(self) -> Optional[str]:
        """Extract text from COMMUNICATION_CREATED event."""
        communication_data = self.get_communication_data()
        if communication_data and communication_data.content:
            return communication_data.content.text
        return None

    def get_conversation_id(self) -> Optional[str]:
        """Extract conversation ID from any event type."""
        if self.event_type in [
            ConversationEventType.CONVERSATION_CREATED,
            ConversationEventType.CONVERSATION_UPDATED,
        ]:
            return self.data.get("id")
        return self.data.get("conversationId")

    def get_profile_id(self) -> Optional[str]:
        """Extract profile ID from PARTICIPANT_ADDED events."""
        participant_data = self.get_participant_data()
        if participant_data:
            return participant_data.profile_id
        return None
