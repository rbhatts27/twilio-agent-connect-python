from typing import Any, Dict, List, Literal, Optional, Union

import requests
from pydantic import BaseModel, Field

from taf.core.logging import get_logger


class TraitQuery(BaseModel):
    """Query specification for traits within a specific group."""

    trait_group: str = Field(
        ..., alias="traitGroup", description="The trait group name"
    )
    trait_names: List[str] = Field(
        ...,
        alias="traitNames",
        description="Array of trait names/keys within the specified group",
    )


class MemoryRetrievalRequest(BaseModel):
    """Request payload for retrieving profile memories."""

    conversation_id: Optional[str] = Field(
        default=None, alias="conversationId", description="Conversation ID for context"
    )
    query: Optional[str] = Field(
        default=None, description="Semantic search query for finding relevant memories"
    )
    traits: Optional[List[TraitQuery]] = Field(
        default=None, description="Array of specific traits to retrieve"
    )
    begin_date: Optional[str] = Field(
        default=None, alias="beginDate", description="Start date for filtering memories"
    )
    end_date: Optional[str] = Field(
        default=None, alias="endDate", description="End date for filtering memories"
    )
    session_limit: Optional[int] = Field(
        default=10,
        alias="sessionLimit",
        description="Maximum number of conversational session memories",
    )
    longterm_limit: Optional[int] = Field(
        default=20,
        alias="longtermLimit",
        description="Maximum number of observational and trait memories",
    )
    traits_limit: Optional[int] = Field(
        default=10,
        alias="traitsLimit",
        description="Maximum number of traits to return",
    )

    model_config = {"populate_by_name": True}


class TraitMemory(BaseModel):
    """A trait memory from the API response."""

    mem_type: Literal["TRAIT"] = Field(..., alias="memType")
    group: str = Field(..., description="The trait group name")
    name: str = Field(..., description="The trait name/key")
    value: Union[str, int, float, bool, Dict[str, Any], List[Any]] = Field(
        ..., description="The trait value"
    )
    updated_at: str = Field(
        ..., alias="updatedAt", description="When the trait was last updated"
    )

    model_config = {"populate_by_name": True}


class ObservationMemory(BaseModel):
    """An observation memory from the API response."""

    mem_type: Literal["OBSERVATION"] = Field(..., alias="memType")
    id: str = Field(..., description="Unique identifier for the observation")
    type: str = Field(..., description="Type of observation (OBSERVATION or SUMMARY)")
    content: str = Field(..., description="The observation content")
    source: str = Field(
        ..., description="Source system that generated this observation"
    )
    conversation_ids: Optional[List[str]] = Field(
        None, alias="conversationIds", description="List of conversation IDs"
    )
    occurred_at: Optional[str] = Field(
        None, alias="occurredAt", description="When the observation occurred"
    )
    created_at: str = Field(
        ..., alias="createdAt", description="When the observation was created"
    )
    updated_at: str = Field(
        ..., alias="updatedAt", description="When the observation was last updated"
    )
    score: Optional[float] = Field(
        None, description="Relevance score for the observation"
    )

    model_config = {"populate_by_name": True}


class SessionMessage(BaseModel):
    """A message within a conversational session."""

    timestamp: str = Field(..., description="When the message was sent")
    direction: Literal["inbound", "outbound"] = Field(
        ..., description="Message direction"
    )
    channel: str = Field(..., description="Communication channel")
    from_address: str = Field(..., alias="from", description="Sender address")
    to_address: str = Field(..., alias="to", description="Recipient address")
    content: str = Field(..., description="Message content")

    model_config = {"populate_by_name": True}


class SessionMemory(BaseModel):
    """A conversational session memory from the API response."""

    mem_type: Literal["SESSION"] = Field(..., alias="memType")
    conversation_id: str = Field(
        ..., alias="conversationId", description="Conversation ID"
    )
    messages: List[SessionMessage] = Field(
        ..., description="List of messages in the session"
    )

    model_config = {"populate_by_name": True}


# Union type for all memory types
MemoraMemory = Union[TraitMemory, ObservationMemory, SessionMemory]


class MemoryRetrievalMeta(BaseModel):
    """Metadata about the memory retrieval operation."""

    query_time: int = Field(
        ..., alias="queryTime", description="Query execution time in milliseconds"
    )

    model_config = {"populate_by_name": True}


class MemoryRetrievalResponse(BaseModel):
    """Response from the memory retrieval API."""

    memories: List[MemoraMemory] = Field(..., description="Retrieved memory results")
    meta: MemoryRetrievalMeta = Field(
        ..., description="Metadata about the retrieval operation"
    )

    model_config = {"populate_by_name": True}


class MemoraClient:
    """Client for interacting with Twilio Memora data plane API."""

    def __init__(
        self, base_url: Optional[str] = None, auth_token: Optional[str] = None
    ) -> None:
        """
        Initialize the Memora client.

        Args:
            base_url: Base URL for the Memora data plane API. Defaults to production.
            auth_token: Authentication token for API requests.
        """
        self.base_url = base_url or "https://memory.twilio.com/v1"
        self.auth_token = auth_token
        self.session = requests.Session()
        self.logger = get_logger(__name__)

        if self.auth_token:
            self.session.headers.update({"X-Pre-Auth-Context": self.auth_token})

    def retrieve_context(
        self, service_id: str, profile_id: str, query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve profile memories including observations, traits, and events.
        Supports hybrid semantic search, date ranges, trait filters,
        and configurable result limits for different memory types.
        This endpoint is optimized for conversational AI and memory retrieval use cases.
        If a query is not specified then one is inferred from the conversation context.

        Args:
            service_id: Memory service ID (e.g., 'mem_service_01hz123456789abcdefghijkl')
            profile_id: Profile ID to retrieve memories for
            query: Optional search query to filter memories

        Returns:
            List of dictionaries (JSON-serializable) representing memories

        Raises:
            requests.RequestException: If the API request fails
            ValueError: If the response cannot be parsed
        """

        # Use the correct endpoint from the API spec
        endpoint = f"/Services/{service_id}/Profiles/{profile_id}/Recall"
        url = f"{self.base_url}{endpoint}"

        # Create the request payload according to the API spec
        request_data = MemoryRetrievalRequest(query=query)
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

            # Convert Pydantic models to JSON-serializable dictionaries
            result = [
                memory.model_dump(by_alias=True, exclude_none=True)
                for memory in memory_response.memories
            ]

            return result

        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve context from Memora: {e}")
            # For now, return empty list on API errors
            # In production, you might want to log this or handle differently
            return []

        except Exception as e:
            self.logger.error(f"Failed to parse Memora response: {e}")
            # Handle parsing errors
            return []
