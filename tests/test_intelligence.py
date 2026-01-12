"""Tests for Conversation Intelligence event processing."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tac.intelligence.operator_result_processor import (
    OperatorResultProcessor,
    ProcessingResult,
    _extract_profile_ids,
    _extract_store_id_from_friendly_name,
    _generate_content,
    _is_test_event,
    _parse_observations_content,
    _parse_summaries_content,
    is_summary_event,
)
from tac.models.intelligence import (
    ClassificationResult,
    CommunicationsRange,
    ExecutionDetails,
    ExtractionEntity,
    ExtractionResult,
    IntelligenceConfiguration,
    JSONResult,
    Operator,
    OperatorResultEvent,
    Participant,
    TextGenerationResult,
    TriggerDetails,
)

# Test fixtures
VALID_STORE_ID = "mem_store_01234567890123456789abcdef"
VALID_PROFILE_ID = "mem_profile_01234567890123456789abcdef"
VALID_CONV_ID = "conv_conversation_01234567890123456789abcdef"


def make_valid_event(
    friendly_name: str = f"MEMORA_{VALID_STORE_ID}",
    operator_friendly_name: str = "Observation Extractor",
    profile_id: str = VALID_PROFILE_ID,
    conversation_id: str = VALID_CONV_ID,
    memory_store_id: str = VALID_STORE_ID,
    result: Any = None,
) -> dict[str, Any]:
    """Create a valid event payload for testing."""
    if result is None:
        result = {"payload": '{"observations": [{"content": "Test observation"}]}'}

    return {
        "id": "test-event-id-123",
        "accountId": "AC00000000000000000000000000000000",
        "conversationId": conversation_id,
        "memoryStoreId": memory_store_id,
        "intelligenceConfiguration": {
            "id": "GA00000000000000000000000000000000",
            "friendlyName": friendly_name,
            "version": 1,
        },
        "operator": {
            "id": "LY00000000000000000000000000000000",
            "friendlyName": operator_friendly_name,
            "version": 1,
        },
        "outputFormat": "JSON",
        "result": result,
        "dateCreated": "2025-01-15T10:30:45Z",
        "referenceIds": [],
        "executionDetails": {
            "trigger": {"on": "conversation_closed", "timestamp": "2025-01-15T10:30:45Z"},
            "participants": [
                {
                    "id": "comms_participant_0123456789abcdefghijklmno",
                    "profileId": profile_id,
                    "type": "CUSTOMER",
                }
            ],
        },
    }


class TestModelParsing:
    """Test Pydantic model parsing."""

    def test_operator_result_event_parsing(self):
        """Test parsing a complete OperatorResultEvent."""
        payload = make_valid_event()
        event = OperatorResultEvent(**payload)

        assert event.id == "test-event-id-123"
        assert event.account_id == "AC00000000000000000000000000000000"
        assert event.conversation_id == VALID_CONV_ID
        assert event.memory_store_id == VALID_STORE_ID
        assert event.output_format == "JSON"
        assert event.date_created == "2025-01-15T10:30:45Z"

    def test_intelligence_configuration_parsing(self):
        """Test IntelligenceConfiguration model."""
        config = IntelligenceConfiguration(
            id="GA123",
            friendly_name="MEMORA_test",
            version=1,
            rule_id="rule_123",
        )
        assert config.id == "GA123"
        assert config.friendly_name == "MEMORA_test"
        assert config.version == 1

    def test_operator_parsing(self):
        """Test Operator model."""
        operator = Operator(
            id="LY123",
            friendly_name="Summary Extractor",
            version=2,
            parameters={"key": "value"},
        )
        assert operator.id == "LY123"
        assert operator.friendly_name == "Summary Extractor"
        assert operator.version == 2
        assert operator.parameters == {"key": "value"}

    def test_participant_parsing(self):
        """Test Participant model."""
        participant = Participant(
            id="comms_participant_123",
            profile_id="mem_profile_123",
            type="CUSTOMER",
        )
        assert participant.id == "comms_participant_123"
        assert participant.profile_id == "mem_profile_123"
        assert participant.type == "CUSTOMER"

    def test_execution_details_parsing(self):
        """Test ExecutionDetails model."""
        details = ExecutionDetails(
            trigger=TriggerDetails(on="utterance", timestamp="2025-01-15T10:30:45Z"),
            communications=CommunicationsRange(first="comm_1", last="comm_2"),
            channels=["SMS", "Voice"],
            participants=[Participant(id="p1")],
            context={"key": "value"},
        )
        assert details.trigger is not None
        assert details.trigger.on == "utterance"
        assert details.channels == ["SMS", "Voice"]

    def test_result_types(self):
        """Test result type models."""
        classification = ClassificationResult(label="positive")
        assert classification.label == "positive"

        extraction = ExtractionResult(entities=[ExtractionEntity(label="PERSON", text="John")])
        assert len(extraction.entities) == 1

        text_gen = TextGenerationResult(result="Generated text", format="text")
        assert text_gen.result == "Generated text"

        json_result = JSONResult(payload='{"key": "value"}')
        assert json_result.payload == '{"key": "value"}'


class TestFilteringLogic:
    """Test event filtering logic."""

    def test_is_test_event_detects_patterns(self):
        """Test test event detection."""
        test_names = [
            "MEMORA_testserviceconfig_123",
            "MEMORA_test_service_456",
            "MEMORA_test-service-789",
            "MEMORA_testservice",
            "MEMORA_TESTSERVICE",  # Case insensitive
        ]
        for name in test_names:
            assert _is_test_event(name), f"Should detect as test: {name}"

    def test_is_test_event_allows_valid(self):
        """Test that valid events are not detected as test."""
        valid_names = [
            "MEMORA_mem_store_123",
            "MEMORA_production_store",
            "MEMORA_my_service",
        ]
        for name in valid_names:
            assert not _is_test_event(name), f"Should not detect as test: {name}"

    def test_extract_store_id_from_friendly_name(self):
        """Test store ID extraction from friendly name."""
        assert _extract_store_id_from_friendly_name("MEMORA_mem_store_123") == "mem_store_123"
        assert _extract_store_id_from_friendly_name("OTHER_mem_store_123") is None
        assert _extract_store_id_from_friendly_name("mem_store_123") is None

    def test_is_summary_event_true(self):
        """Test summary event detection."""
        payload = make_valid_event(operator_friendly_name="Summary Extractor")
        event = OperatorResultEvent(**payload)
        assert is_summary_event(event) is True

    def test_is_summary_event_false(self):
        """Test observation event detection."""
        payload = make_valid_event(operator_friendly_name="Observation Extractor")
        event = OperatorResultEvent(**payload)
        assert is_summary_event(event) is False

        # Test with other names
        payload = make_valid_event(operator_friendly_name="Other Operator")
        event = OperatorResultEvent(**payload)
        assert is_summary_event(event) is False


class TestProfileExtraction:
    """Test profile ID extraction."""

    def test_extract_profile_ids_valid(self):
        """Test extracting valid profile IDs."""
        payload = make_valid_event()
        event = OperatorResultEvent(**payload)
        profile_ids = _extract_profile_ids(event)
        assert len(profile_ids) == 1
        assert profile_ids[0] == VALID_PROFILE_ID

    def test_extract_profile_ids_multiple(self):
        """Test extracting multiple profile IDs."""
        second_profile_id = "mem_profile_11234567890123456789abcdef"
        payload = make_valid_event()
        payload["executionDetails"]["participants"] = [
            {
                "id": "p1",
                "profileId": VALID_PROFILE_ID,
                "type": "CUSTOMER",
            },
            {
                "id": "p2",
                "profileId": second_profile_id,
                "type": "AGENT",
            },
        ]
        event = OperatorResultEvent(**payload)
        profile_ids = _extract_profile_ids(event)
        assert len(profile_ids) == 2

    def test_extract_profile_ids_accepts_any_format(self):
        """Test that all profile IDs are accepted regardless of format."""
        payload = make_valid_event()
        payload["executionDetails"]["participants"] = [
            {"id": "p1", "profileId": "any_profile_id", "type": "CUSTOMER"},
            {
                "id": "p2",
                "profileId": VALID_PROFILE_ID,
                "type": "AGENT",
            },
        ]
        event = OperatorResultEvent(**payload)
        profile_ids = _extract_profile_ids(event)
        assert len(profile_ids) == 2
        assert profile_ids[0] == "any_profile_id"
        assert profile_ids[1] == VALID_PROFILE_ID

    def test_extract_profile_ids_empty_participants(self):
        """Test extraction with no participants."""
        payload = make_valid_event()
        payload["executionDetails"]["participants"] = []
        event = OperatorResultEvent(**payload)
        profile_ids = _extract_profile_ids(event)
        assert len(profile_ids) == 0


class TestContentGeneration:
    """Test content generation from event results."""

    def test_generate_content_json(self):
        """Test JSON content generation."""
        payload = make_valid_event(result={"payload": '{"observations": [{"content": "test"}]}'})
        event = OperatorResultEvent(**payload)
        content = _generate_content(event)
        assert content == '{"observations": [{"content": "test"}]}'

    def test_generate_content_classification(self):
        """Test classification content generation."""
        payload = make_valid_event(result={"label": "positive"})
        payload["outputFormat"] = "CLASSIFICATION"
        event = OperatorResultEvent(**payload)
        content = _generate_content(event)
        assert content == "positive"

    def test_generate_content_text(self):
        """Test text generation content."""
        payload = make_valid_event(result={"result": "Generated text content"})
        payload["outputFormat"] = "TEXT"
        event = OperatorResultEvent(**payload)
        content = _generate_content(event)
        assert content == "Generated text content"


class TestContentParsing:
    """Test content parsing for observations and summaries."""

    def test_parse_observations_array_format(self):
        """Test parsing observations array format."""
        json_content = '{"observations": [{"content": "obs1"}, {"content": "obs2"}]}'
        contents = _parse_observations_content(json_content)
        assert len(contents) == 2
        assert contents[0] == "obs1"
        assert contents[1] == "obs2"

    def test_parse_observations_fallback(self):
        """Test observations fallback to raw content."""
        json_content = "Raw observation content"
        contents = _parse_observations_content(json_content)
        assert len(contents) == 1
        assert contents[0] == "Raw observation content"

    def test_parse_observations_empty_array(self):
        """Test parsing empty observations array."""
        json_content = '{"observations": []}'
        contents = _parse_observations_content(json_content)
        assert len(contents) == 1  # Fallback to raw content
        assert contents[0] == '{"observations": []}'

    def test_parse_summaries_array_format(self):
        """Test parsing summaries array format."""
        json_content = '{"summaries": [{"summary": "sum1"}, {"summary": "sum2"}]}'
        contents = _parse_summaries_content(json_content)
        assert len(contents) == 2
        assert contents[0] == "sum1"
        assert contents[1] == "sum2"

    def test_parse_summaries_single_format(self):
        """Test parsing single summary format."""
        json_content = '{"summary": "Single summary content"}'
        contents = _parse_summaries_content(json_content)
        assert len(contents) == 1
        assert contents[0] == "Single summary content"

    def test_parse_summaries_fallback(self):
        """Test summaries fallback to raw content."""
        json_content = "Raw summary content"
        contents = _parse_summaries_content(json_content)
        assert len(contents) == 1
        assert contents[0] == "Raw summary content"


class TestOperatorResultProcessor:
    """Test the OperatorResultProcessor class."""

    @pytest.fixture
    def mock_memory_client(self):
        """Create a mock memory client."""
        client = MagicMock()
        client.create_observation = AsyncMock(return_value={"id": "obs_123"})
        client.create_conversation_summaries = AsyncMock(return_value={"message": "Success"})
        return client

    @pytest.fixture
    def processor(self, mock_memory_client):
        """Create a processor with mock client."""
        return OperatorResultProcessor(mock_memory_client)

    @pytest.mark.asyncio
    async def test_process_event_skips_non_memora(self, processor):
        """Test that non-MEMORA events are skipped."""
        payload = make_valid_event(friendly_name="OTHER_config")
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.skipped is True
        assert "Non-memora" in result.skip_reason

    @pytest.mark.asyncio
    async def test_process_event_skips_test_events(self, processor):
        """Test that test events are skipped."""
        payload = make_valid_event(friendly_name="MEMORA_testservice_123")
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.skipped is True
        assert "Test event" in result.skip_reason

    @pytest.mark.asyncio
    async def test_process_event_requires_profile_ids(self, processor):
        """Test that profile IDs are required."""
        payload = make_valid_event()
        payload["executionDetails"]["participants"] = []
        result = await processor.process_event(payload)

        assert result.success is False
        assert "No profile IDs" in result.error

    @pytest.mark.asyncio
    async def test_process_observation_event_success(self, processor, mock_memory_client):
        """Test successful observation event processing."""
        payload = make_valid_event(
            result={"payload": '{"observations": [{"content": "Test observation"}]}'}
        )
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.event_type == "observation"
        assert result.created_count == 1
        mock_memory_client.create_observation.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_summary_event_success(self, processor, mock_memory_client):
        """Test successful summary event processing."""
        payload = make_valid_event(
            operator_friendly_name="Summary Extractor",
            result={"payload": '{"summary": "Test summary content"}'},
        )
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.event_type == "summary"
        assert result.created_count == 1
        mock_memory_client.create_conversation_summaries.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_event_multiple_profiles(self, processor, mock_memory_client):
        """Test processing with multiple profiles."""
        second_profile_id = "mem_profile_11234567890123456789abcdef"
        payload = make_valid_event(result={"payload": '{"observations": [{"content": "Test"}]}'})
        payload["executionDetails"]["participants"] = [
            {
                "id": "p1",
                "profileId": VALID_PROFILE_ID,
                "type": "CUSTOMER",
            },
            {
                "id": "p2",
                "profileId": second_profile_id,
                "type": "AGENT",
            },
        ]
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.created_count == 2  # One for each profile
        assert mock_memory_client.create_observation.call_count == 2

    @pytest.mark.asyncio
    async def test_process_event_multiple_observations(self, processor, mock_memory_client):
        """Test processing multiple observations from one event."""
        payload = make_valid_event(
            result={"payload": '{"observations": [{"content": "Obs1"}, {"content": "Obs2"}]}'}
        )
        result = await processor.process_event(payload)

        assert result.success is True
        assert result.created_count == 2
        assert mock_memory_client.create_observation.call_count == 2

    @pytest.mark.asyncio
    async def test_process_event_api_error_handling(self, processor, mock_memory_client):
        """Test handling of API errors."""
        mock_memory_client.create_observation.side_effect = Exception("API Error")
        payload = make_valid_event(result={"payload": '{"observations": [{"content": "Test"}]}'})
        result = await processor.process_event(payload)

        assert result.success is False
        assert "Failed to create observation" in result.error

    @pytest.mark.asyncio
    async def test_process_event_invalid_payload(self, processor):
        """Test handling of invalid payload."""
        payload = {"invalid": "payload"}
        result = await processor.process_event(payload)

        assert result.success is False
        assert "Failed to parse event payload" in result.error

    @pytest.mark.asyncio
    async def test_process_event_uses_memory_store_id(self, processor, mock_memory_client):
        """Test that memory_store_id is used when available."""
        payload = make_valid_event(
            memory_store_id=VALID_STORE_ID,
            result={"payload": '{"observations": [{"content": "Test"}]}'},
        )
        result = await processor.process_event(payload)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_event_extracts_store_id_from_friendly_name(
        self, processor, mock_memory_client
    ):
        """Test fallback to extracting store ID from friendly name."""
        payload = make_valid_event(
            friendly_name=f"MEMORA_{VALID_STORE_ID}",
            memory_store_id=None,
            result={"payload": '{"observations": [{"content": "Test"}]}'},
        )
        # Remove memory_store_id
        del payload["memoryStoreId"]

        result = await processor.process_event(payload)

        assert result.success is True


class TestProcessingResult:
    """Test ProcessingResult model."""

    def test_processing_result_success(self):
        """Test successful processing result."""
        result = ProcessingResult(
            success=True,
            event_type="observation",
            created_count=5,
        )
        assert result.success is True
        assert result.event_type == "observation"
        assert result.created_count == 5
        assert result.skipped is False
        assert result.error is None

    def test_processing_result_skipped(self):
        """Test skipped processing result."""
        result = ProcessingResult(
            success=True,
            skipped=True,
            skip_reason="Non-memora event",
        )
        assert result.success is True
        assert result.skipped is True
        assert result.skip_reason == "Non-memora event"

    def test_processing_result_error(self):
        """Test error processing result."""
        result = ProcessingResult(
            success=False,
            error="Validation failed",
        )
        assert result.success is False
        assert result.error == "Validation failed"
