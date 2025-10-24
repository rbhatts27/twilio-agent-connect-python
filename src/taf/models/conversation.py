"""Pydantic models for Twilio Maestro Conversation API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ParticipantAddress(BaseModel):
    """Communication address for a conversation participant."""

    communication_type: Literal["VOICE", "SMS"] = Field(
        ..., alias="communicationType", description="Type of communication (VOICE or SMS)"
    )
    value: str = Field(..., description="Address value (phone number)")

    model_config = {"populate_by_name": True}


class ConversationRequest(BaseModel):
    """Request payload for creating a conversation."""

    name: Optional[str] = Field(None, description="Conversation name")
    layers: Optional[list[str]] = Field(None, description="List of conversation layers")
    intelligence_agents: Optional[list[str]] = Field(
        None, description="List of intelligence agent TTIDs"
    )

    model_config = {"populate_by_name": True}


class ConversationResponse(BaseModel):
    """Response from creating a conversation."""

    id: str = Field(..., description="Conversation ID")
    account_id: str = Field(..., description="Twilio Account SID")

    service_id: Optional[str] = Field(None, description="Conversation Service SID")
    status: Optional[str] = Field(None, description="Conversation status")
    name: Optional[str] = Field(None, description="Conversation name")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    layers: Optional[list[str]] = Field(default_factory=list, description="Conversation layers")
    intelligence_agents: Optional[list[str]] = Field(
        default_factory=list, description="Intelligence agents"
    )

    model_config = {"populate_by_name": True}


class ParticipantRequest(BaseModel):
    """Request payload for creating a conversation participant."""

    name: Optional[str] = Field(default=None, description="Display name for the participant")
    label: Optional[str] = Field(default=None, description="Grouping string")
    profile_id: Optional[str] = Field(default=None, description="Resolved segment profile")
    addresses: Optional[list[ParticipantAddress]] = Field(
        default_factory=list, description="List of communication addresses for the participant"
    )

    model_config = {"populate_by_name": True}


class ParticipantResponse(BaseModel):
    """Response from creating a participant."""

    id: str = Field(..., description="Participant ID")
    conversation_id: str = Field(..., description="Conversation ID")
    account_id: str = Field(..., description="Twilio Account SID")
    service_id: Optional[str] = Field(None, description="Conversation Service SID")
    name: str = Field(..., description="Participant name")

    label: Optional[str] = Field(None, description="Participant label")
    profile_id: Optional[str] = Field(None, description="Profile ID")
    status: Optional[str] = Field(None, description="Participant status")
    addresses: list[ParticipantAddress] = Field(
        default_factory=list, description="List of communication addresses for the participant"
    )
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    model_config = {"populate_by_name": True}
