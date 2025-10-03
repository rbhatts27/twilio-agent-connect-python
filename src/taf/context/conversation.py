from typing import Any, List, Optional

import requests
from pydantic import BaseModel, Field

from taf.core.logging import get_logger


class ConversationResponse(BaseModel):
    """Response from creating a conversation."""

    id: str = Field(..., description="Conversation ID")
    account_sid: str = Field(..., description="Twilio Account SID")
    status: str = Field(..., description="Conversation status")
    name: Optional[str] = Field(None, description="Conversation name")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    layers: List[Any] = Field(default_factory=list, description="Conversation layers")
    intelligence_agents: List[Any] = Field(
        default_factory=list, description="Intelligence agents"
    )
    status_callback: Optional[str] = Field(None, description="Status callback URL")

    model_config = {"populate_by_name": True}


class ParticipantRequest(BaseModel):
    """Request payload for creating a conversation participant."""

    profile_id: str = Field(..., description="Profile ID to add as participant")

    model_config = {"populate_by_name": True}


class ParticipantResponse(BaseModel):
    """Response from creating a participant."""

    id: str = Field(..., description="Participant ID")
    conversation_id: str = Field(..., description="Conversation ID")
    account_sid: str = Field(..., description="Twilio Account SID")
    name: Optional[str] = Field(None, description="Participant name")
    label: Optional[str] = Field(None, description="Participant label")
    profile_id: str = Field(..., description="Profile ID")
    status: str = Field(..., description="Participant status")
    addresses: List[Any] = Field(
        default_factory=list, description="Participant addresses"
    )
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

    model_config = {"populate_by_name": True}


class ConversationClient:
    """Client for interacting with Maestro API."""

    def __init__(
        self, base_url: Optional[str] = None, account_sid: Optional[str] = None
    ) -> None:
        """
        Initialize the Conversation client.

        Args:
            base_url: Base URL for the Maestro API
            account_sid: Twilio Account SID for authentication
        """
        self.base_url = base_url
        self.account_sid = account_sid
        self.session = requests.Session()
        self.logger = get_logger(__name__)

        if self.account_sid:
            self.session.headers.update(
                {
                    "X-Twilio-Account-Sid": self.account_sid,
                    "Content-Type": "application/json",
                }
            )

    def add_participant(
        self, conversation_id: str, profile_id: str
    ) -> ParticipantResponse:
        """
        Add a new participant to a conversation.

        Args:
            conversation_id: The conversation ID to add participant to
            profile_id: The profile ID to add as participant

        Returns:
            ParticipantResponse object containing the created participant details

        Raises:
            requests.RequestException: If the API request fails
        """

        if not self.base_url:
            self.logger.error("base_url must be configured but was None")
            raise ValueError("base_url must be configured")

        url = f"{self.base_url}/Conversations/{conversation_id}/Participants"

        request_data = ParticipantRequest(profile_id=profile_id)
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            response = self.session.post(url, json=request_payload)
            response.raise_for_status()
            participant = ParticipantResponse(**response.json())
            return participant

        except requests.RequestException as e:
            self.logger.error(f"Failed to add participant: {e}")
            raise

    def create_conversation(self) -> ConversationResponse:
        """
        Create a new conversation.

        Returns:
            ConversationResponse object containing the created conversation details

        Raises:
            requests.RequestException: If the API request fails
        """

        if not self.base_url:
            self.logger.error("base_url must be configured but was None")
            raise ValueError("base_url must be configured")

        url = f"{self.base_url}/Conversations"

        try:
            response = self.session.post(url, json={})
            response.raise_for_status()
            conversation = ConversationResponse(**response.json())
            return conversation

        except requests.RequestException as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise
