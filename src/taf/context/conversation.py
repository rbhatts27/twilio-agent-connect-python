from typing import Optional

import requests

from taf.core.logging import get_logger
from taf.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ParticipantAddress,
    ParticipantRequest,
    ParticipantResponse,
)


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
        addresses: Optional[list[ParticipantAddress]] = None,
    ) -> ParticipantResponse:
        """
        Add a new participant to a conversation.

        Args:
            conversation_id: The conversation ID to add participant to
            addresses: List of communication addresses for the participant (optional)

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

        request_data = ParticipantRequest(addresses=addresses)
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

    def list_participants(self, conversation_id: str) -> list[ParticipantResponse]:
        url = (
            f"{self.base_url}/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Participants"
        )

        try:
            response = self.session.get(url)
            response.raise_for_status()
            participants = response.json().get("participants", [])
            return [ParticipantResponse(**p) for p in participants]
        except requests.Timeout:
            self.logger.error(f"Timeout listing participants for conversation {conversation_id}")
            raise
        except requests.RequestException as e:
            self.logger.error(
                f"HTTP error listing participants for conversation {conversation_id}: {e}"
            )
            raise
        except ValueError as e:
            self.logger.error(f"Invalid JSON format when listing participants: {e}")
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
