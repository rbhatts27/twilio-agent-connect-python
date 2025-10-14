from typing import Any, Optional

import requests
from pydantic import BaseModel, Field

from taf.core.logging import get_logger


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

    name: Optional[str] = Field(None, description="Display name for the participant")
    label: Optional[str] = Field(None, description="Grouping string")
    profile_id: Optional[str] = Field(None, description="Resolved segment profile")
    addresses: Optional[list[Any]] = Field(
        default_factory=list, description="Participant addresses"
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
    addresses: list[Any] = Field(default_factory=list, description="Participant addresses")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    model_config = {"populate_by_name": True}


class ConversationClient:
    """Client for interacting with Maestro API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        account_sid: Optional[str] = None,
        service_id: Optional[str] = None,
    ) -> None:
        """
        Initialize the Conversation client.

        Args:
            base_url: Base URL for the Maestro API
            account_sid: Twilio Account SID for authentication
            service_id: Conversation Service SID for API requests
        """
        self.base_url = base_url
        self.account_sid = account_sid
        self.service_id = service_id
        self.session = requests.Session()
        self.logger = get_logger(__name__)

        if self.account_sid:
            # todo: use rest proxy auth when Memora supports it
            self.session.headers.update(
                {
                    "I-Twilio-Auth-Account": self.account_sid,
                    "Content-Type": "application/json",
                }
            )

    def add_participant(
        self,
        conversation_id: str,
        name: Optional[str],
        label: Optional[str],
        profile_id: Optional[str],
    ) -> ParticipantResponse:
        """
        Add a new participant to a conversation.

        Args:
            conversation_id: The conversation ID to add participant to
            name: Display name for the participant (optional)
            label: Grouping string for the participant (optional)
            profile_id: The profile ID to add as participant (optional)

        Returns:
            ParticipantResponse object containing the created participant details

        Raises:
            requests.RequestException: If the API request fails
        """

        if not self.base_url:
            self.logger.error("base_url must be configured but was None")
            raise ValueError("base_url must be configured")

        url = (
            f"{self.base_url}/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Participants"
        )

        request_data = ParticipantRequest(name=name, label=label, profile_id=profile_id)
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            response = self.session.post(
                url,
                json=request_payload,
            )
            response.raise_for_status()
            participant = ParticipantResponse(**response.json())
            return participant

        except requests.RequestException as e:
            self.logger.error(f"Failed to add participant: {e}")
            raise

    def create_conversation(
        self,
        name: Optional[str] = None,
        layers: Optional[list[str]] = None,
        intelligence_agents: Optional[list[str]] = None,
    ) -> ConversationResponse:
        """
        Create a new conversation.

        Args:
            name: Conversation name (optional)
            layers: List of available conversation layers (optional)
            intelligence_agents: List of intelligence agent TTIDs (optional)

        Returns:
            ConversationResponse object containing the created conversation details

        Raises:
            requests.RequestException: If the API request fails
        """

        if not self.base_url:
            self.logger.error("base_url must be configured but was None")
            raise ValueError("base_url must be configured")

        url = f"{self.base_url}/Services/{self.service_id}/Conversations"

        request_data = ConversationRequest(
            name=name, layers=layers, intelligence_agents=intelligence_agents
        )
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            response = self.session.post(
                url,
                json=request_payload,
            )
            response.raise_for_status()
            conversation = ConversationResponse(**response.json())
            return conversation

        except requests.RequestException as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise
