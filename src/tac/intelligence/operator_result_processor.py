"""Processor for Conversation Intelligence webhook events.

Logic ported from:
https://github.com/twilio-internal/memora-domain/blob/main/services/common/cintel-events-processor/internal/transformer/transformer.go
"""

import json
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError

from tac.context.memory import MemoryClient
from tac.core.logging import get_logger
from tac.models.intelligence import OperatorResultEvent

# Test event patterns to filter out
TEST_PATTERNS = [
    "testserviceconfig",
    "test_service",
    "test-service",
    "testservice",
]


class ProcessingResult(BaseModel):
    """Result of processing a CI webhook event."""

    success: bool = Field(
        ...,
        description="Whether processing completed successfully",
    )
    event_type: Optional[str] = Field(
        default=None,
        description="Type of event processed: 'observation', 'summary', or None if filtered/failed",
    )
    skipped: bool = Field(
        default=False,
        description="True if event was filtered out (not an error)",
    )
    skip_reason: Optional[str] = Field(
        default=None,
        description="Reason for skipping (e.g., 'non-memora event')",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if processing failed",
    )
    created_count: int = Field(
        default=0,
        description="Number of observations/summaries created",
    )

    model_config = {"populate_by_name": True}


def is_summary_event(event: OperatorResultEvent) -> bool:
    """
    Check if event represents a Summary (vs Observation) based on operator.friendly_name.

    Args:
        event: The operator result event to check

    Returns:
        True if this is a summary event, False for observation
    """
    friendly_name = event.operator.friendly_name if event.operator else None
    return friendly_name == "Summary Extractor"


def _is_test_event(friendly_name: str) -> bool:
    """
    Check if an event is a test event that should be discarded.

    Args:
        friendly_name: The intelligence configuration friendly name

    Returns:
        True if this is a test event
    """
    friendly_name_lower = friendly_name.lower()
    return any(pattern in friendly_name_lower for pattern in TEST_PATTERNS)


def _extract_store_id_from_friendly_name(friendly_name: str) -> Optional[str]:
    """
    Extract store ID from the IntelligenceConfiguration.friendlyName.

    Format expected: "MEMORA_#{MEMORY_STORE_TTID}"

    Args:
        friendly_name: The intelligence configuration friendly name

    Returns:
        The extracted store ID or None
    """
    if not friendly_name.startswith("MEMORA_"):
        return None
    return friendly_name[7:]  # Strip "MEMORA_" prefix


def _extract_profile_ids(event: OperatorResultEvent) -> list[str]:
    """
    Extract valid profile IDs from event participants.

    Args:
        event: The operator result event

    Returns:
        List of valid profile IDs
    """
    profile_ids: list[str] = []

    if not event.execution_details or not event.execution_details.participants:
        return profile_ids

    for participant in event.execution_details.participants:
        if participant.profile_id:
            profile_ids.append(participant.profile_id)

    return profile_ids


def _generate_content(event: OperatorResultEvent) -> Optional[str]:
    """
    Generate content string from the event result based on output format.

    Args:
        event: The operator result event

    Returns:
        The content string or None if unable to extract
    """
    output_format = event.output_format.upper()
    result = event.result

    # Handle different result formats
    if output_format == "JSON":
        # For JSON format, extract payload
        if isinstance(result, dict):
            if "payload" in result:
                return str(result["payload"])
            # Handle nested union structure
            if "com.twilio.cai.intelligence.JSONResult" in result:
                nested = result["com.twilio.cai.intelligence.JSONResult"]
                if isinstance(nested, dict) and "payload" in nested:
                    return str(nested["payload"])
        return json.dumps(result) if result else None

    elif output_format == "CLASSIFICATION":
        if isinstance(result, dict) and "label" in result:
            return str(result["label"])
        return str(result) if result else None

    elif output_format == "EXTRACTION":
        if isinstance(result, dict) and "entities" in result:
            return json.dumps(result["entities"])
        return json.dumps(result) if result else None

    elif output_format in ("TEXT", "GENERATION"):
        if isinstance(result, dict) and "result" in result:
            return str(result["result"])
        return str(result) if result else None

    # Fallback: serialize result as JSON
    return json.dumps(result) if result else None


def _parse_observations_content(json_content: str) -> list[str]:
    """
    Parse JSON content to extract individual observation contents.

    Expected format: {"observations": [{"content": "..."}, {"content": "..."}]}
    Fallback: Treat raw content as single observation

    Args:
        json_content: The JSON content string

    Returns:
        List of observation content strings
    """
    try:
        payload = json.loads(json_content)
        if isinstance(payload, dict) and "observations" in payload:
            observations = payload["observations"]
            if isinstance(observations, list):
                contents = []
                for obs in observations:
                    if isinstance(obs, dict) and obs.get("content"):
                        contents.append(str(obs["content"]))
                if contents:
                    return contents
    except (json.JSONDecodeError, TypeError):
        # If parsing fails or the structure is unexpected, fall back to treating
        # the entire input as a single summary in the return statement below.
        pass

    # Fallback: treat entire content as single observation
    return [json_content] if json_content else []


def _parse_summaries_content(json_content: str) -> list[str]:
    """
    Parse JSON content to extract individual summary contents.

    Supported formats:
    1. Array: {"summaries": [{"summary": "..."}, {"summary": "..."}]}
    2. Single: {"summary": "..."}
    3. Fallback: Treat raw content as single summary

    Args:
        json_content: The JSON content string

    Returns:
        List of summary content strings
    """
    try:
        payload = json.loads(json_content)

        # Try array format first
        if isinstance(payload, dict) and "summaries" in payload:
            summaries = payload["summaries"]
            if isinstance(summaries, list):
                contents = []
                for summary in summaries:
                    if isinstance(summary, dict) and summary.get("summary"):
                        contents.append(str(summary["summary"]))
                if contents:
                    return contents

        # Try single summary format
        if isinstance(payload, dict) and "summary" in payload:
            summary_content = payload["summary"]
            if summary_content:
                return [str(summary_content)]

    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: treat entire content as single summary
    return [json_content] if json_content else []


class OperatorResultProcessor:
    """Processor for Conversation Intelligence webhook events.

    This processor handles incoming CI webhook payloads, validates them,
    and creates observations or summaries in Memora based on the event type.

    Example usage:
        ```python
        from tac.context.memory import MemoryClient
        from tac.intelligence import OperatorResultProcessor

        memory_client = MemoryClient(...)
        processor = OperatorResultProcessor(memory_client)

        result = await processor.process_event(webhook_payload)
        if result.success:
            print(f"Created {result.created_count} {result.event_type}(s)")
        elif result.skipped:
            print(f"Skipped: {result.skip_reason}")
        else:
            print(f"Error: {result.error}")
        ```
    """

    def __init__(self, memory_client: MemoryClient) -> None:
        """
        Initialize the CI event processor.

        Args:
            memory_client: MemoryClient instance for creating observations/summaries
        """
        self.memory_client = memory_client
        self.logger = get_logger(__name__)

    async def process_event(self, payload: dict[str, Any]) -> ProcessingResult:
        """
        Process a CI webhook payload.

        This method:
        1. Parses the payload into an OperatorResultEvent (Pydantic validates required fields)
        2. Applies filtering logic (MEMORA_ prefix, test events)
        3. Extracts profile IDs and store ID
        4. Generates content from the result
        5. Creates observations or summaries in Memora

        Args:
            payload: The raw webhook payload dictionary

        Returns:
            ProcessingResult with status and details
        """
        # Parse payload into OperatorResultEvent (Pydantic validates required fields)
        try:
            event = OperatorResultEvent(**payload)
        except ValidationError as e:
            self.logger.error(f"Failed to parse event payload: {e}")
            return ProcessingResult(
                success=False,
                error=f"Failed to parse event payload: {e}",
            )

        # Filter by MEMORA_ prefix
        friendly_name = event.intelligence_configuration.friendly_name or ""
        if not friendly_name.startswith("MEMORA_"):
            self.logger.debug(
                f"Discarding non-memory event - does not have MEMORA_ prefix: {event.id}"
            )
            return ProcessingResult(
                success=True,
                skipped=True,
                skip_reason="Non-memora event (missing MEMORA_ prefix)",
            )

        # Filter test events
        if _is_test_event(friendly_name):
            self.logger.debug(f"Discarding test event: {event.id}")
            return ProcessingResult(
                success=True,
                skipped=True,
                skip_reason="Test event",
            )

        # Extract profile IDs
        profile_ids = _extract_profile_ids(event)
        if not profile_ids:
            error_msg = f"No profile IDs found in event {event.id}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error=error_msg,
            )

        # Extract store ID
        store_id = event.memory_store_id or _extract_store_id_from_friendly_name(friendly_name)

        if not store_id:
            error_msg = f"No store ID found in event {event.id}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error=error_msg,
            )

        # Generate content from result
        content = _generate_content(event)
        if not content:
            error_msg = f"Failed to generate content from event {event.id}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                error=error_msg,
            )

        # Determine event type and process
        if is_summary_event(event):
            return await self._process_summary_event(
                event=event,
                content=content,
                profile_ids=profile_ids,
                store_id=store_id,
            )
        else:
            return await self._process_observation_event(
                event=event,
                content=content,
                profile_ids=profile_ids,
                store_id=store_id,
            )

    async def _process_observation_event(
        self,
        event: OperatorResultEvent,
        content: str,
        profile_ids: list[str],
        store_id: str,
    ) -> ProcessingResult:
        """
        Process an observation event by creating observations in Memora.

        Args:
            event: The parsed operator result event
            content: The generated content string
            profile_ids: List of profile IDs to create observations for
            store_id: The memory store ID

        Returns:
            ProcessingResult with status and count
        """
        # Parse observations from content
        observation_contents = _parse_observations_content(content)

        if not observation_contents:
            self.logger.info(f"No observations to create from event {event.id}")
            return ProcessingResult(
                success=True,
                event_type="observation",
                skipped=True,
                skip_reason="No observation content found",
            )

        created_count = 0
        errors: list[str] = []

        # Create observations for each profile
        for profile_id in profile_ids:
            for obs_content in observation_contents:
                try:
                    await self.memory_client.create_observation(
                        profile_id=profile_id,
                        content=obs_content,
                        source="conversation-intelligence",
                        conversation_ids=[event.conversation_id],
                        occurred_at=event.date_created,
                    )
                    created_count += 1
                except Exception as e:
                    error_msg = f"Failed to create observation for profile {profile_id}: {e}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)

        if created_count == 0 and errors:
            return ProcessingResult(
                success=False,
                event_type="observation",
                error="; ".join(errors),
            )

        self.logger.info(f"Created {created_count} observation(s) from event {event.id}")
        return ProcessingResult(
            success=True,
            event_type="observation",
            created_count=created_count,
        )

    async def _process_summary_event(
        self,
        event: OperatorResultEvent,
        content: str,
        profile_ids: list[str],
        store_id: str,
    ) -> ProcessingResult:
        """
        Process a summary event by creating conversation summaries in Memora.

        Args:
            event: The parsed operator result event
            content: The generated content string
            profile_ids: List of profile IDs to create summaries for
            store_id: The memory store ID

        Returns:
            ProcessingResult with status and count
        """
        # Parse summaries from content
        summary_contents = _parse_summaries_content(content)

        if not summary_contents:
            self.logger.info(f"No summaries to create from event {event.id}")
            return ProcessingResult(
                success=True,
                event_type="summary",
                skipped=True,
                skip_reason="No summary content found",
            )

        created_count = 0
        errors: list[str] = []

        # Create summaries for each profile
        for profile_id in profile_ids:
            # Build summaries payload
            summaries_payload: list[dict[str, Any]] = []
            for summary_content in summary_contents:
                summaries_payload.append(
                    {
                        "content": summary_content,
                        "conversationId": event.conversation_id,
                        "occurredAt": event.date_created,
                        "source": "conversation-intelligence",
                    }
                )

            try:
                await self.memory_client.create_conversation_summaries(
                    profile_id=profile_id,
                    summaries=summaries_payload,
                )
                created_count += len(summaries_payload)
            except Exception as e:
                error_msg = f"Failed to create summaries for profile {profile_id}: {e}"
                self.logger.error(error_msg)
                errors.append(error_msg)

        if created_count == 0 and errors:
            return ProcessingResult(
                success=False,
                event_type="summary",
                error="; ".join(errors),
            )

        self.logger.info(f"Created {created_count} summary(ies) from event {event.id}")
        return ProcessingResult(
            success=True,
            event_type="summary",
            created_count=created_count,
        )
