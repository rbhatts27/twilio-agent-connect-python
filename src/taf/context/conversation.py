from typing import Any, Literal, Optional

import httpx

from taf.core.logging import get_logger
from taf.models.conversation import (
    Communication,
    CommunicationRequest,
    CommunicationsListResponse,
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
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.logger = get_logger(__name__)

    def _get_client(self) -> httpx.AsyncClient:
        """Create a new httpx.AsyncClient for each request to avoid event loop issues."""
        return httpx.AsyncClient(
            auth=(self.account_sid, self.auth_token),
            timeout=30.0,
        )

    async def add_participant(
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
            httpx.HTTPError: If the API request fails
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
            async with self._get_client() as client:
                response = await client.post(
                    url,
                    json=request_payload,
                )
                response.raise_for_status()
                participant = ParticipantResponse(**response.json())
                return participant

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to add participant: {e}")
            raise

    async def list_participants(self, conversation_id: str) -> list[ParticipantResponse]:
        url = (
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Participants"
        )

        try:
            async with self._get_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                participants = response.json().get("participants", [])
                return [ParticipantResponse(**p) for p in participants]
        except httpx.TimeoutException:
            self.logger.error(f"Timeout listing participants for conversation {conversation_id}")
            return []
        except httpx.HTTPError as e:
            self.logger.error(
                f"HTTP error listing participants for conversation {conversation_id}: {e}"
            )
            return []
        except ValueError as e:
            self.logger.error(f"Invalid JSON format when listing participants: {e}")
            return []

    async def create_conversation(
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
            httpx.HTTPError: If the API request fails
        """
        url = f"{self.base_url}/v2/Services/{self.service_id}/Conversations"

        request_data = ConversationRequest(name=name)
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            async with self._get_client() as client:
                response = await client.post(
                    url,
                    json=request_payload,
                )
                response.raise_for_status()
                conversation = ConversationResponse(**response.json())
                return conversation

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to create conversation: {e}")
            raise

    async def add_communication(
        self,
        conversation_id: str,
        communication_request: CommunicationRequest,
    ) -> Communication:
        """
        Add a new communication to a conversation.

        Args:
            conversation_id: The conversation ID to add communication to
            communication_request: CommunicationRequest object with author, content, and recipients

        Returns:
            Communication object containing the created communication details

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = (
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Communications"
        )

        request_payload = communication_request.model_dump(by_alias=True, exclude_none=True)

        try:
            async with self._get_client() as client:
                response = await client.post(
                    url,
                    json=request_payload,
                )
                response.raise_for_status()
                communication = Communication(**response.json())
                return communication

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to add communication: {e}")
            raise

    async def list_communications(
        self,
        conversation_id: str,
        channel_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> list[Communication]:
        """
        List communications for a conversation.

        Args:
            conversation_id: The conversation ID to list communications for
            channel_id: Optional channel ID filter (call ID, message ID, etc.)
            page_size: Maximum number of items to return (1-1000)
            page_token: Token for pagination

        Returns:
            List of Communication objects

        Raises:
            httpx.HTTPError: If the API request fails
        """
        url = (
            f"{self.base_url}/v2/Services/{self.service_id}/Conversations/"
            f"{conversation_id}/Communications"
        )

        # Build query parameters
        params: dict[str, Any] = {}
        if channel_id:
            params["channelId"] = channel_id
        if page_size:
            params["pageSize"] = page_size
        if page_token:
            params["pageToken"] = page_token

        try:
            async with self._get_client() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                communications_list = CommunicationsListResponse(**response.json())
                return communications_list.communications

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to list communications: {e}")
            raise
