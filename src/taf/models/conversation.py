"""Pydantic models for Twilio Maestro Conversation API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


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
