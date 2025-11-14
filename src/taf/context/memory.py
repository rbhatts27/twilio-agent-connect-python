from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from taf.core.logging import get_logger
from taf.models.memory import (
    MemoryRetrievalMeta,
    MemoryRetrievalRequest,
    MemoryRetrievalResponse,
    ProfileResponse,
)


class MemoryClient:
    """Client for interacting with Twilio Memora data plane API."""

    def __init__(
        self,
        base_url: str,
        store_id: str,
        api_key: str,
        api_token: str,
    ) -> None:
        """
        Initialize the Memory client.

        Args:
            base_url: Base URL for the Memora data plane API.
            store_id: Memory store ID (starts with MG).
            api_key: API Key for Memora authentication.
            api_token: API Token for Memora authentication.
        """
        self.base_url = base_url
        self.store_id = store_id
        self.session = requests.Session()
        self.logger = get_logger(__name__)
        self.session.auth = HTTPBasicAuth(api_key, api_token)

    def retrieve_memory(
        self,
        profile_id: str,
        conversation_id: Optional[str] = None,
        query: Optional[str] = None,
    ) -> MemoryRetrievalResponse:
        """
        Retrieve conversation memories including observations, sessions, and summaries.
        Supports semantic search and uses default limits for different memory types.
        This endpoint is optimized for conversational AI and memory retrieval use cases.

        Args:
            profile_id: Profile ID using Twilio Type ID (TTID) format
            conversation_id: Optional conversation ID using Twilio Type ID (TTID) format
            query: Optional semantic search query for finding relevant memories (1-1024 characters)

        Returns:
            MemoryRetrievalResponse containing observations, summaries, sessions, and metadata

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response cannot be parsed
        """

        # Use the correct endpoint from the API spec
        endpoint = f"/v1/Services/{self.store_id}/Profiles/{profile_id}/Recall"
        url = f"{self.base_url}{endpoint}"

        # Create the request payload with default values
        request_data = MemoryRetrievalRequest(
            query=query,
        )
        request_payload = request_data.model_dump(by_alias=True, exclude_none=True)

        try:
            # POST request with JSON body as per API spec
            response = self.session.post(
                url,
                json=request_payload,
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
                meta=MemoryRetrievalMeta(queryTime=0),
            )

        except Exception as e:
            self.logger.error(f"Failed to parse Memora response: {e}")
            # Return empty response on parsing errors
            return MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )

    def get_profile(
        self,
        profile_id: str,
        trait_groups: Optional[list[str]] = None,
    ) -> ProfileResponse:
        """
        Retrieve a profile by ID with optional trait group selection.

        Args:
            profile_id: Profile ID using Twilio Type ID (TTID) format
            trait_groups: Optional list of trait group names to include in the response

        Returns:
            ProfileResponse containing profile ID, creation timestamp, and traits

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response cannot be parsed
        """
        # Build the endpoint URL
        endpoint = f"/v1/Services/{self.store_id}/Profiles/{profile_id}"
        url = f"{self.base_url}{endpoint}"

        # Build query parameters
        params = {}
        if trait_groups:
            # Convert list to comma-separated string
            params["traitGroups"] = ",".join(trait_groups)

        try:
            # GET request with query parameters
            response = self.session.get(url, params=params)
            response.raise_for_status()

            # Parse the response
            data = response.json()
            profile_response = ProfileResponse(**data)

            return profile_response

        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve profile from Memora: {e}")
            raise

        except Exception as e:
            self.logger.error(f"Failed to parse Memora profile response: {e}")
            raise
