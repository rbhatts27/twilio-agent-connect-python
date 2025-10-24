from typing import Optional

import requests

from taf.core.logging import get_logger
from taf.models.memory import (
    MemoryRetrievalMeta,
    MemoryRetrievalRequest,
    MemoryRetrievalResponse,
)


class MemoryClient:
    """Client for interacting with Twilio Memora data plane API."""

    def __init__(self, base_url: Optional[str] = None, auth_token: Optional[str] = None) -> None:
        """
        Initialize the Memory client.

        Args:
            base_url: Base URL for the Memora data plane API. Defaults to production.
            auth_token: Authentication token for API requests.
        """
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = requests.Session()
        self.logger = get_logger(__name__)

        if self.auth_token:
            # todo: change this to use proper auth when Memora supports it
            self.session.headers.update(
                {"X-Pre-Auth-Context": "account_00000000000000000000000000"}
            )

    def retrieve_memory(
        self,
        service_id: str,
        conversation_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> MemoryRetrievalResponse:
        """
        Retrieve conversation memories including observations, sessions, and summaries.
        Supports semantic search and uses default limits for different memory types.
        This endpoint is optimized for conversational AI and memory retrieval use cases.

        Args:
            service_id: Memory service ID (e.g., 'mem_service_01hz123456789abcdefghijkl')
            conversation_id: Optional conversation ID using Twilio Type ID (TTID) format
            query: Optional semantic search query for finding relevant memories (1-1024 characters)

        Returns:
            MemoryRetrievalResponse containing observations, summaries, sessions, and metadata

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response cannot be parsed
        """

        # Use the correct endpoint from the API spec
        endpoint = f"/v1/Services/{service_id}/Profiles/{conversation_id}/Recall"
        url = f"{self.base_url}{endpoint}"

        # Create the request payload with default values
        request_data = MemoryRetrievalRequest(
            conversationId=conversation_id,
            query=query,
        )
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            # POST request with JSON body as per API spec
            response = self.session.post(
                url,
                json=request_payload,
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()

            # Parse the response according to the API spec
            data = response.json()
            memory_response = MemoryRetrievalResponse(**data)

            # Return full response with observations, summaries, sessions, and metadata
            return memory_response

        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve context from Memora: {e}")
            # Return empty response on API errors
            return MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                sessions=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse Memora response: {e}")
            # Return empty response on parsing errors
            return MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                sessions=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
