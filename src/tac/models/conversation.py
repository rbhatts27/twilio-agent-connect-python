"""Pydantic models for Twilio Maestro Conversation API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from tac.models.pagination import PaginationMeta


class ParticipantAddress(BaseModel):
    """Communication address for a conversation participant."""

    channel: Literal["VOICE", "SMS", "RCS", "EMAIL", "WHATSAPP", "CHAT", "API", "SYSTEM"] = Field(
        ..., description="The channel for Communication (VOICE, SMS, EMAIL, etc.)"
    )
    address: str = Field(..., description="The address value (phone number, email, etc.)")
    channel_id: Optional[str] = Field(
        default=None,
        alias="channelId",
        description="Channel-specific ID for correlating Communications",
    )

    model_config = {"populate_by_name": True}


class ConversationConfiguration(BaseModel):
    """Configuration settings for a conversation."""

    intelligence_service_ids: Optional[list[str]] = Field(
        None,
        alias="intelligenceServiceIds",
        description="List of Intelligence Service IDs associated with this Conversation",
    )

    model_config = {"populate_by_name": True}


class ConversationRequest(BaseModel):
    """Request payload for creating a conversation."""

    name: Optional[str] = Field(default=None, description="Conversation name")
    configuration: Optional[ConversationConfiguration] = Field(
        default=None, description="Conversation configuration settings"
    )

    model_config = {"populate_by_name": True}


class UpdateConversationRequest(BaseModel):
    """Request payload for updating a conversation."""

    name: Optional[str] = Field(default=None, description="Conversation name")
    status: Optional[Literal["ACTIVE", "INACTIVE", "CLOSED"]] = Field(
        default=None, description="Conversation state (ACTIVE/INACTIVE/CLOSED)"
    )
    configuration: Optional[ConversationConfiguration] = Field(
        default=None, description="Conversation configuration settings"
    )

    model_config = {"populate_by_name": True}


class ConversationResponse(BaseModel):
    """Response from creating a conversation."""

    id: str = Field(..., description="Conversation ID")
    account_id: Optional[str] = Field(None, description="Twilio Account SID")

    service_id: Optional[str] = Field(None, description="Conversation Service SID")
    status: Optional[str] = Field(None, description="Conversation status")
    name: Optional[str] = Field(None, description="Conversation name")
    configuration: Optional[ConversationConfiguration] = Field(
        None, description="Conversation configuration settings"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    model_config = {"populate_by_name": True}


class ParticipantRequest(BaseModel):
    """Request payload for creating a conversation participant."""

    name: Optional[str] = Field(default=None, description="Display name for the Participant")
    type: Optional[Literal["HUMAN_AGENT", "CUSTOMER", "AI_AGENT"]] = Field(
        default=None, description="Type of Participant in the Conversation"
    )
    profile_id: Optional[str] = Field(
        default=None, alias="profileId", description="Resolved segment profile"
    )
    addresses: Optional[list[ParticipantAddress]] = Field(
        default_factory=list, description="List of Communication addresses for the Participant"
    )

    model_config = {"populate_by_name": True}


class ParticipantResponse(BaseModel):
    """Response from creating a participant."""

    id: str = Field(..., description="Participant ID")
    conversation_id: str = Field(..., alias="conversationId", description="Conversation ID")
    account_id: str = Field(..., alias="accountId", description="Account ID")
    service_id: Optional[str] = Field(
        None, alias="serviceId", description="Conversation Service ID"
    )
    name: Optional[str] = Field(None, description="Participant display name")
    type: Optional[Literal["HUMAN_AGENT", "CUSTOMER", "AI_AGENT"]] = Field(
        None, description="Type of Participant in the Conversation"
    )
    profile_id: Optional[str] = Field(None, alias="profileId", description="Segment profile ID")
    addresses: list[ParticipantAddress] = Field(
        default_factory=list, description="Communication addresses for this Participant"
    )
    created_at: Optional[str] = Field(
        None, alias="createdAt", description="Timestamp when this Participant was created"
    )
    updated_at: Optional[str] = Field(
        None, alias="updatedAt", description="Timestamp when this Participant was last updated"
    )

    model_config = {"populate_by_name": True}


class CommunicationParticipant(BaseModel):
    """Author or recipient in a communication."""

    address: str = Field(
        ...,
        max_length=254,
        description="Address of the participant (e.g., phone number, email address)",
        json_schema_extra={"example": "+12025551234"},
    )
    channel: Literal["VOICE", "SMS", "RCS", "EMAIL", "WHATSAPP", "CHAT", "API", "SYSTEM"] = Field(
        ..., description="The channel for the communication"
    )
    participant_id: Optional[str] = Field(
        default=None,
        alias="participantId",
        description="Participant identifier",
        json_schema_extra={"example": "comms_participant_00000000000000000000000000"},
    )

    model_config = {"populate_by_name": True}


class CommunicationContent(BaseModel):
    """Content of a communication."""

    type: Literal["TEXT", "TRANSCRIPTION"] = Field("TEXT", description="Content type")
    text: Optional[str] = Field(
        default=None,
        max_length=8388608,
        description="Primary text content (optional)",
        json_schema_extra={"example": "Hello, I need help with my account"},
    )

    model_config = {"populate_by_name": True}


class Communication(BaseModel):
    """A communication representing a message exchanged in a conversation."""

    id: str = Field(
        ...,
        description="Unique communication identifier",
        json_schema_extra={"example": "comms_communication_00000000000000000000000000"},
    )
    author: CommunicationParticipant = Field(..., description="Author of the communication")
    content: CommunicationContent = Field(..., description="Content of the communication")
    recipients: list[CommunicationParticipant] = Field(..., description="Communication recipients")
    channel_id: Optional[str] = Field(
        default=None,
        alias="channelId",
        description="Channel-specific ID (optional)",
        json_schema_extra={"example": "SM00000000000000000000000000000000"},
    )
    created_at: str = Field(
        ...,
        alias="createdAt",
        max_length=30,
        description="When communication was created",
        json_schema_extra={"example": "2025-01-15T10:15:30Z"},
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        max_length=30,
        description="When communication was last updated",
        json_schema_extra={"example": "2025-01-15T10:20:30Z"},
    )

    model_config = {"populate_by_name": True}


class CommunicationRequest(BaseModel):
    """Request payload for adding a communication."""

    author: CommunicationParticipant = Field(..., description="Author of the communication")
    content: CommunicationContent = Field(..., description="Content of the communication")
    recipients: list[CommunicationParticipant] = Field(
        ..., description="List of recipients for the communication"
    )

    model_config = {"populate_by_name": True}


class CommunicationsListResponse(BaseModel):
    """Response from list communications endpoint."""

    communications: list[Communication] = Field(..., description="List of communications")
    meta: PaginationMeta = Field(..., description="Pagination metadata")

    model_config = {"populate_by_name": True}


class ConversationsListResponse(BaseModel):
    """Response from list conversations endpoint."""

    conversations: list[ConversationResponse] = Field(..., description="List of conversations")
    meta: PaginationMeta = Field(..., description="Pagination metadata")

    model_config = {"populate_by_name": True}
