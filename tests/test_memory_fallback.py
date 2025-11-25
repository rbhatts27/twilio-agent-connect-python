"""Tests for memory retrieval fallback functionality."""

from unittest.mock import patch

import pytest
import requests

from taf import TAF, TAFConfig
from taf.models.conversation import Communication, CommunicationContent, CommunicationParticipant
from taf.models.memory import MemoryRetrievalMeta, MemoryRetrievalResponse
from taf.models.session import ConversationSession


def get_test_config_without_memory():
    """Get test configuration without Twilio Memory."""
    return {
        "twilio_auth_token": "test_token_123",
        "environment": "prod",
        "twilio_account_sid": "ACtest123",
        "conversation_service_sid": "IS123test",
        "twilio_phone_number": "+15551234567",
    }


def get_test_config_with_memory():
    """Get test configuration with Twilio Memory."""
    config = get_test_config_without_memory()
    config["twilio_memory_config"] = {
        "memory_store_id": "MGtest123",
        "api_key": "test_api_key",
        "api_token": "test_api_token",
    }
    return config


class TestMemoryFallback:
    """Test memory retrieval fallback to Maestro Communications API."""

    @patch("taf.context.memory.MemoryClient.retrieve_memory")
    def test_retrieve_memory_with_memora_configured(self, mock_retrieve):
        """Test retrieve_memory uses Memora when configured."""
        # Setup
        config = TAFConfig(**get_test_config_with_memory())
        taf = TAF(config)

        mock_retrieve.return_value = MemoryRetrievalResponse(
            observations=[],
            summaries=[],
            communications=[],
            meta=MemoryRetrievalMeta(queryTime=100),
        )

        context = ConversationSession(
            conversation_id="CH123",
            profile_id="profile_123",
            channel="SMS",
        )

        # Execute
        result = taf.retrieve_memory(context, query="test query")

        # Verify
        mock_retrieve.assert_called_once_with(
            profile_id="profile_123",
            conversation_id="CH123",
            query="test query",
        )
        assert isinstance(result, MemoryRetrievalResponse)
        assert result.meta.query_time == 100

    def test_retrieve_memory_memora_configured_without_profile_id_raises(self):
        """Test retrieve_memory raises error when Memora configured but profile_id missing."""
        # Setup
        config = TAFConfig(**get_test_config_with_memory())
        taf = TAF(config)

        context = ConversationSession(
            conversation_id="CH123",
            profile_id=None,  # Missing profile_id
            channel="SMS",
        )

        # Execute & Verify
        with pytest.raises(ValueError, match="profile_id is required"):
            taf.retrieve_memory(context)

    @patch("taf.context.conversation.ConversationClient.list_communications")
    def test_retrieve_memory_fallback_to_maestro(self, mock_list_comms):
        """Test retrieve_memory falls back to Maestro when Memora not configured."""
        # Setup
        config = TAFConfig(**get_test_config_without_memory())
        taf = TAF(config)

        # Mock Maestro communications response
        mock_list_comms.return_value = [
            Communication(
                id="comm_123",
                author=CommunicationParticipant(
                    address="+12025551234",
                    channel="SMS",
                    participantId="part_123",
                ),
                content=CommunicationContent(type="TEXT", text="Hello"),
                recipients=[
                    CommunicationParticipant(
                        address="+12025555678",
                        channel="SMS",
                        participantId="part_456",
                    )
                ],
                createdAt="2019-08-24T14:15:22Z",
                updatedAt="2019-08-24T14:15:22Z",
            )
        ]

        context = ConversationSession(
            conversation_id="CH123",
            profile_id=None,  # profile_id not required for fallback
            channel="SMS",
        )

        # Execute
        result = taf.retrieve_memory(context, query="test query")

        # Verify
        mock_list_comms.assert_called_once_with(conversation_id="CH123")

        # Check response structure
        assert isinstance(result, MemoryRetrievalResponse)
        assert len(result.observations) == 0
        assert len(result.summaries) == 0
        assert len(result.communications) == 1

        # Check communication conversion
        comm = result.communications[0]
        assert comm.id == "comm_123"
        assert comm.author.address == "+12025551234"
        assert comm.content.text == "Hello"
        assert len(comm.recipients) == 1

    @patch("taf.context.conversation.ConversationClient.list_communications")
    def test_retrieve_memory_fallback_with_empty_communications(self, mock_list_comms):
        """Test retrieve_memory fallback handles empty communications list."""
        # Setup
        config = TAFConfig(**get_test_config_without_memory())
        taf = TAF(config)

        mock_list_comms.return_value = []

        context = ConversationSession(
            conversation_id="CH123",
            profile_id=None,
            channel="SMS",
        )

        # Execute
        result = taf.retrieve_memory(context)

        # Verify
        assert isinstance(result, MemoryRetrievalResponse)
        assert len(result.observations) == 0
        assert len(result.summaries) == 0
        assert len(result.communications) == 0
        assert result.meta.query_time is None  # query_time is optional with default None

    @patch("taf.context.conversation.ConversationClient.list_communications")
    def test_retrieve_memory_fallback_api_error(self, mock_list_comms):
        """Test retrieve_memory fallback propagates API errors."""
        # Setup
        config = TAFConfig(**get_test_config_without_memory())
        taf = TAF(config)

        mock_list_comms.side_effect = requests.RequestException("Maestro API Error")

        context = ConversationSession(
            conversation_id="CH123",
            profile_id=None,
            channel="SMS",
        )

        # Execute & Verify
        with pytest.raises(requests.RequestException, match="Maestro API Error"):
            taf.retrieve_memory(context)

    @patch("taf.context.conversation.ConversationClient.list_communications")
    def test_retrieve_memory_fallback_with_multiple_communications(self, mock_list_comms):
        """Test retrieve_memory fallback with multiple communications."""
        # Setup
        config = TAFConfig(**get_test_config_without_memory())
        taf = TAF(config)

        mock_list_comms.return_value = [
            Communication(
                id=f"comm_{i}",
                author=CommunicationParticipant(
                    address="+12025551234",
                    channel="SMS",
                    participantId="part_123",
                ),
                content=CommunicationContent(type="TEXT", text=f"Message {i}"),
                recipients=[
                    CommunicationParticipant(
                        address="+12025555678",
                        channel="SMS",
                        participantId="part_456",
                    )
                ],
                createdAt="2019-08-24T14:15:22Z",
                updatedAt="2019-08-24T14:15:22Z",
            )
            for i in range(5)
        ]

        context = ConversationSession(
            conversation_id="CH123",
            profile_id=None,
            channel="SMS",
        )

        # Execute
        result = taf.retrieve_memory(context)

        # Verify
        assert len(result.communications) == 5
        for i, comm in enumerate(result.communications):
            assert comm.id == f"comm_{i}"
            assert comm.content.text == f"Message {i}"

    def test_is_twilio_memory_enabled_with_memory(self):
        """Test is_twilio_memory_enabled returns True when configured."""
        config = TAFConfig(**get_test_config_with_memory())
        taf = TAF(config)

        assert taf.is_twilio_memory_enabled() is True

    def test_is_twilio_memory_enabled_without_memory(self):
        """Test is_twilio_memory_enabled returns False when not configured."""
        config = TAFConfig(**get_test_config_without_memory())
        taf = TAF(config)

        assert taf.is_twilio_memory_enabled() is False
