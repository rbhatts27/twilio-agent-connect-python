from typing import Literal, Optional

import requests
from pydantic import BaseModel, Field

from taf.core.logging import get_logger


class MemoryRetrievalRequest(BaseModel):
    """Request payload for retrieving conversation memories."""

    conversation_id: Optional[str] = Field(
        default=None,
        alias="conversationId",
        description="A unique identifier for the conversation using Twilio Type ID (TTID) format",
        json_schema_extra={"example": "comms_conversation_00000000000000000000000000"},
    )
    query: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1024,
        description="Semantic search query for finding relevant memories",
        json_schema_extra={"example": "customer satisfaction feedback"},
    )
    begin_date: Optional[str] = Field(
        default=None,
        alias="beginDate",
        max_length=30,
        description="Start date for filtering memories (inclusive)",
        json_schema_extra={"example": "2025-01-01T00:00:00Z"},
    )
    end_date: Optional[str] = Field(
        default=None,
        alias="endDate",
        max_length=30,
        description="End date for filtering memories (exclusive)",
        json_schema_extra={"example": "2025-01-31T23:59:59Z"},
    )
    sessions_limit: Optional[int] = Field(
        default=10,
        alias="sessionsLimit",
        ge=1,
        le=100,
        description="Maximum number of conversational session memories to return",
        json_schema_extra={"example": 10},
    )
    observations_limit: Optional[int] = Field(
        default=20,
        alias="observationsLimit",
        ge=1,
        le=100,
        description="Maximum number of observation memories to return",
        json_schema_extra={"example": 20},
    )
    summaries_limit: Optional[int] = Field(
        default=5,
        alias="summariesLimit",
        ge=1,
        le=100,
        description="Maximum number of summary memories to return",
        json_schema_extra={"example": 5},
    )

    model_config = {"populate_by_name": True}


class CiOperator(BaseModel):
    """Information about the Conversational Intelligence operator."""

    ci_service_id: str = Field(
        ...,
        alias="ciServiceId",
        max_length=34,
        description="SID of the Conversational Intelligence Service",
        json_schema_extra={"example": "GA00000000000000000000000000000000"},
    )
    id: str = Field(
        ...,
        max_length=34,
        description="ID of the language operator that extracted this observation",
        json_schema_extra={"example": "LY00000000000000000000000000000000"},
    )
    version: str = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Version of the language operator that extracted this observation",
        json_schema_extra={"example": "1.2.3"},
    )

    model_config = {"populate_by_name": True}


class ObservationInfo(BaseModel):
    """An observation memory from the API response."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The main content of the observation",
        json_schema_extra={
            "example": "Customer expressed satisfaction with recent product update."
        },
    )
    source: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Source system that generated this observation",
        json_schema_extra={"example": "conversational-intelligence"},
    )
    id: str = Field(
        ...,
        description="Unique identifier for the observation using Twilio Type ID (TTID) format",
        json_schema_extra={"example": "mem_observation_00000000000000000000000000"},
    )
    created_at: str = Field(
        ...,
        alias="createdAt",
        max_length=30,
        description="Timestamp when the observation was created",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )
    updated_at: str = Field(
        ...,
        alias="updatedAt",
        max_length=30,
        description="Timestamp when the observation was last updated",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )
    occurred_at: Optional[str] = Field(
        default=None,
        alias="occurredAt",
        max_length=30,
        description="Timestamp when the observation originally occurred",
        json_schema_extra={"example": "2025-01-15T10:15:30Z"},
    )
    conversation_ids: Optional[list[str]] = Field(
        default=None,
        alias="conversationIds",
        max_length=10,
        description="Array of conversation IDs associated with this observation",
        json_schema_extra={"example": ["comms_conversation_00000000000000000000000000"]},
    )
    ci_operator: Optional[CiOperator] = Field(
        default=None,
        alias="ciOperator",
        description="Information about the CI operator that extracted this observation",
    )
    confidence: Optional[Literal["HIGH", "MEDIUM", "LOW"]] = Field(
        default=None,
        description="Confidence level for the observation extraction",
        json_schema_extra={"example": "HIGH"},
    )

    model_config = {"populate_by_name": True}


class SummaryInfo(BaseModel):
    """A summary memory derived from observations at the end of conversations."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The main content of the summary",
        json_schema_extra={
            "example": "Customer discussed billing concerns and was satisfied with resolution."
        },
    )
    conversation_id: str = Field(
        ...,
        alias="conversationId",
        description="Unique identifier for the conversation using Twilio Type ID (TTID) format",
        json_schema_extra={"example": "comms_conversation_00000000000000000000000000"},
    )
    id: str = Field(
        ...,
        description="Unique identifier for the summary using Twilio Type ID (TTID) format",
        json_schema_extra={"example": "mem_summary_00000000000000000000000000"},
    )
    created_at: str = Field(
        ...,
        alias="createdAt",
        max_length=30,
        description="Timestamp when the summary was created",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )
    updated_at: str = Field(
        ...,
        alias="updatedAt",
        max_length=30,
        description="Timestamp when the summary was last updated",
        json_schema_extra={"example": "2025-01-15T10:30:45Z"},
    )
    source: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Source system that generated the summary",
        json_schema_extra={"example": "conversations"},
    )
    occurred_at: Optional[str] = Field(
        default=None,
        alias="occurredAt",
        max_length=30,
        description="Timestamp when the summary was originally created",
        json_schema_extra={"example": "2025-01-15T10:15:30Z"},
    )
    ci_operator: Optional[CiOperator] = Field(
        default=None,
        alias="ciOperator",
        description="Information about the CI operator that extracted this observation",
    )

    model_config = {"populate_by_name": True}


class SessionMessage(BaseModel):
    """A message within a conversational session."""

    timestamp: str = Field(
        ...,
        max_length=30,
        description="When the message was sent",
        json_schema_extra={"example": "2025-01-15T15:58:10Z"},
    )
    direction: Literal["inbound", "outbound"] = Field(
        ..., description="Message direction relative to the profile"
    )
    channel: str = Field(
        ...,
        max_length=30,
        description="Communication channel (case-insensitive)",
        json_schema_extra={"example": "sms"},
    )
    from_address: str = Field(
        ...,
        alias="from",
        max_length=128,
        description="Sender address (phone number or identifier)",
        json_schema_extra={"example": "+15551234567"},
    )
    to_address: str = Field(
        ...,
        alias="to",
        max_length=128,
        description="Recipient address (phone number or identifier)",
        json_schema_extra={"example": "+15557654321"},
    )
    content: str = Field(
        ...,
        max_length=4096,
        description="Message body content (may be truncated)",
        json_schema_extra={"example": "Thanks for checking in."},
    )

    model_config = {"populate_by_name": True}


class SessionInfo(BaseModel):
    """A session memory containing recent conversation context."""

    conversation_id: str = Field(
        ...,
        alias="conversationId",
        description="Unique identifier for the conversation using Twilio Type ID (TTID) format",
        json_schema_extra={"example": "comms_conversation_00000000000000000000000000"},
    )
    messages: list[SessionMessage] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Chronologically ordered list of recent messages (oldest first)",
    )

    model_config = {"populate_by_name": True}


class MemoryRetrievalMeta(BaseModel):
    """Metadata about the memory retrieval operation."""

    query_time: int = Field(
        ...,
        alias="queryTime",
        ge=0,
        le=600000,
        description="Query execution time in milliseconds",
        json_schema_extra={"example": 156},
    )

    model_config = {"populate_by_name": True}


class MemoryRetrievalResponse(BaseModel):
    """Response from the memory retrieval API."""

    observations: list[ObservationInfo] = Field(
        ..., max_length=100, description="Array of observation memories"
    )
    summaries: list[SummaryInfo] = Field(
        ..., max_length=100, description="Array of summary memories from end of conversations"
    )
    sessions: list[SessionInfo] = Field(
        ...,
        max_length=100,
        description="Array of session memories with recent conversation context",
    )
    meta: MemoryRetrievalMeta = Field(..., description="Metadata about the retrieval operation")

    model_config = {"populate_by_name": True}


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
