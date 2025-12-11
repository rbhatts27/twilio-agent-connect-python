"""Models for Twilio Conversation Events."""

import json
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ConversationEventType(str, Enum):
    """Enum for Maestro Conversation Event types."""

    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_UPDATED = "conversation.updated"
    PARTICIPANT_ADDED = "participant.added"
    COMMUNICATION_CREATED = "communication.created"


class TranscriptionWord(BaseModel):
    """Represents a single word in a transcription."""

    text: Optional[str] = None
    start_time: Optional[str] = Field(None, alias="startTime")
    end_time: Optional[str] = Field(None, alias="endTime")
    alternates: Optional[list[str]] = None

    model_config = {"populate_by_name": True}


class TranscriptionMetadata(BaseModel):
    """Metadata for conversation transcription."""

    channel: Optional[int] = None
    confidence: Optional[float] = None
    end_time: Optional[str] = Field(None, alias="endTime")
    words: Optional[list[TranscriptionWord]] = None

    model_config = {"populate_by_name": True}


class CommunicationRecipient(BaseModel):
    """Represents a recipient of a communication."""

    participant_id: Optional[str] = Field(None, alias="participantId")
    channel: Optional[str] = None
    status: Optional[str] = None

    model_config = {"populate_by_name": True}


class ConversationEvent(BaseModel):
    """Represents a Twilio Conversation Event."""

    event_type: Optional[str] = Field(None, alias="EventType")
    timestamp: Optional[str] = Field(None, alias="Timestamp")
    account_id: Optional[str] = Field(None, alias="AccountId")
    configuration_id: Optional[str] = Field(None, alias="ConfigurationId")
    language: Optional[str] = Field(None, alias="Language")

    # Conversation fields
    conversation_id: Optional[str] = Field(None, alias="ConversationId")
    conversation_name: Optional[str] = Field(None, alias="ConversationName")
    conversation_status: Optional[str] = Field(None, alias="ConversationStatus")

    # Participant fields
    participant_id: Optional[str] = Field(None, alias="ParticipantId")
    participant_name: Optional[str] = Field(None, alias="ParticipantName")
    participant_type: Optional[Literal["HUMAN_AGENT", "CUSTOMER", "AI_AGENT", "UNKNOWN"]] = Field(
        None, alias="ParticipantType"
    )
    profile_id: Optional[str] = Field(None, alias="ProfileId")

    # Communication fields
    communication_id: Optional[str] = Field(None, alias="CommunicationId")
    author_participant_id: Optional[str] = Field(None, alias="AuthorParticipantId")
    author_address: Optional[str] = Field(None, alias="AuthorAddress")
    author_channel: Optional[str] = Field(None, alias="AuthorChannel")
    body: Optional[str] = Field(None, alias="Body")

    model_config = {"populate_by_name": True}

    def get_message_text(self) -> Optional[str]:
        """Extract text from the Body field (which may be JSON)."""
        if not self.body:
            return None

        # Try to parse as JSON
        try:
            body_data = json.loads(self.body)
            if isinstance(body_data, dict) and "text" in body_data:
                text_value = body_data["text"]
                return str(text_value) if text_value is not None else None
        except (json.JSONDecodeError, ValueError):
            pass

        # If not JSON or parsing fails, return as-is
        return self.body
