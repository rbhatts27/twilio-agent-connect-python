"""Models for Twilio Conversation Events."""

from typing import Optional

from pydantic import BaseModel, Field


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

    event_type: Optional[str] = Field(None, alias="eventType")
    event_timestamp: Optional[str] = Field(None, alias="eventTimestamp")
    account_id: Optional[str] = Field(None, alias="accountId")
    service_id: Optional[str] = Field(None, alias="serviceId")
    conversation_id: Optional[str] = Field(None, alias="conversationId")
    conversation_name: Optional[str] = Field(None, alias="conversationName")
    conversation_status: Optional[str] = Field(None, alias="conversationStatus")
    conversation_layers: Optional[list[str]] = Field(None, alias="conversationLayers")
    conversation_intelligence_agents: Optional[list[str]] = Field(
        None, alias="conversationIntelligenceAgents"
    )
    conversation_transcription_metadata: Optional[TranscriptionMetadata] = Field(
        None, alias="conversationTranscriptionMetadata"
    )
    participant_id: Optional[str] = Field(None, alias="participantId")
    participant_name: Optional[str] = Field(None, alias="participantName")
    participant_label: Optional[str] = Field(None, alias="participantLabel")
    participant_profile_id: Optional[str] = Field(None, alias="participantProfileId")
    participant_profile_service_id: Optional[str] = Field(None, alias="participantProfileServiceId")
    participant_status: Optional[str] = Field(None, alias="participantStatus")
    communication_id: Optional[str] = Field(None, alias="communicationId")
    communication_status: Optional[str] = Field(None, alias="communicationStatus")
    communication_channel: Optional[str] = Field(None, alias="communicationChannel")
    communication_message_body: Optional[str] = Field(None, alias="communicationMessageBody")
    communication_message_author: Optional[str] = Field(None, alias="communicationMessageAuthor")
    communication_recipients: Optional[list[CommunicationRecipient]] = Field(
        None, alias="communicationRecipients"
    )
    communication_channel_id: Optional[str] = Field(None, alias="communicationChannelId")
    communication_reference_ids: Optional[list[str]] = Field(
        None, alias="communicationReferenceIds"
    )
    communication_language: Optional[str] = Field(None, alias="communicationLanguage")

    model_config = {"populate_by_name": True}


class TwilioConversationEvent(BaseModel):
    """Represents a Twilio Conversations webhook event (form-encoded format)."""

    messaging_service_sid: Optional[str] = Field(None, alias="MessagingServiceSid")
    event_type: Optional[str] = Field(None, alias="EventType")
    attributes: Optional[str] = Field(None, alias="Attributes")
    date_created: Optional[str] = Field(None, alias="DateCreated")
    index: Optional[int] = Field(None, alias="Index")
    chat_service_sid: Optional[str] = Field(None, alias="ChatServiceSid")
    message_sid: Optional[str] = Field(None, alias="MessageSid")
    account_sid: Optional[str] = Field(None, alias="AccountSid")
    source: Optional[str] = Field(None, alias="Source")
    retry_count: Optional[int] = Field(None, alias="RetryCount")
    author: Optional[str] = Field(None, alias="Author")
    participant_sid: Optional[str] = Field(None, alias="ParticipantSid")
    body: Optional[str] = Field(None, alias="Body")
    conversation_sid: Optional[str] = Field(None, alias="ConversationSid")
    profile_id: Optional[str] = Field(None, alias="ProfileId")

    model_config = {"populate_by_name": True}
