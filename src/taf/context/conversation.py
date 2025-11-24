from typing import Literal, Optional

import requests
from requests.auth import HTTPBasicAuth

from taf.core.logging import get_logger
from taf.models.conversation import (
    CommunicationRequest,
    CommunicationResponse,
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
        base_url: str,
        account_sid: str,
        auth_token: str,
        service_id: str,
    ) -> None:
        """
        Initialize the Conversation client.

        Args:
            base_url: Base URL for the Maestro API
            account_sid: Twilio Account SID for authentication
            auth_token: Twilio Auth Token for authentication
            service_id: Conversation Service SID for API requests
        """
        self.base_url = base_url
        self.service_id = service_id
        self.session = requests.Session()
        self.logger = get_logger(__name__)
        self.session.auth = HTTPBasicAuth(account_sid, auth_token)

    def add_participant(
        self,
        conversation_id: str,
        addresses: Optional[list[ParticipantAddress]] = None,
        participant_type: Literal["HUMAN_AGENT", "CUSTOMER", "AI_AGENT"] = "CUSTOMER",
        profile_id: Optional[str] = None,
    ) -> ParticipantResponse:
        """
        Add a new participant to a conversation.

        Args:
            conversation_id: The conversation ID to add participant to
            addresses: List of communication addresses for the participant (optional)
            participant_type: Type of participant (e.g., "CUSTOMER", "AGENT").
                Defaults to "CUSTOMER"
            profile_id: Optional profile ID to associate with the participant for memory retrieval

        Returns:
            ParticipantResponse object containing the created participant details

        Raises:
            requests.RequestException: If the API request fails
        """
        url = (
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Participants"
        )

        request_data = ParticipantRequest(addresses=addresses, type=participant_type)
        if profile_id:
            request_data.profile_id = profile_id
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
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Participants"
        )

        try:
            response = self.session.get(url)
            response.raise_for_status()
            participants = response.json().get("participants", [])
            return [ParticipantResponse(**p) for p in participants]
        except requests.Timeout:
            self.logger.error(f"Timeout listing participants for conversation {conversation_id}")
            return []
        except requests.RequestException as e:
            self.logger.error(
                f"HTTP error listing participants for conversation {conversation_id}: {e}"
            )
            return []
        except ValueError as e:
            self.logger.error(f"Invalid JSON format when listing participants: {e}")
            return []

    def create_conversation(
        self,
        name: Optional[str] = None,
    ) -> ConversationResponse:
        """
        Create a new conversation.

        Args:
            name: Conversation name (optional)

        Returns:
            ConversationResponse object containing the created conversation details

        Raises:
            requests.RequestException: If the API request fails
        """
        url = f"{self.base_url}/v2/Services/{self.service_id}/Conversations"

        request_data = ConversationRequest(name=name)
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

    def add_communication(
        self,
        conversation_id: str,
        communication_request: CommunicationRequest,
    ) -> CommunicationResponse:
        """
        Add a new communication to a conversation.

        Args:
            conversation_id: The conversation ID to add communication to
            communication_request: CommunicationRequest object with author, content, and recipients

        Returns:
            CommunicationResponse object containing the created communication details

        Raises:
            requests.RequestException: If the API request fails
        """
        url = (
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Communications"
        )

        request_payload = communication_request.model_dump(by_alias=True, exclude_none=True)

        try:
            response = self.session.post(
                url,
                json=request_payload,
            )
            response.raise_for_status()
            communication = CommunicationResponse(**response.json())
            return communication

        except requests.RequestException as e:
            self.logger.error(f"Failed to add communication: {e}")
            raise
