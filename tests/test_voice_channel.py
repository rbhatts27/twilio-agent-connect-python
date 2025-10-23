"""Tests for Voice Channel."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taf import TAF
from taf.channels.voice import VoiceChannel
from taf.context.conversation import ConversationResponse
from taf.context.memory import MemoryRetrievalMeta, MemoryRetrievalResponse
from taf.core.context import ConversationSession


def get_test_config() -> dict:
    """Get a valid test configuration."""
    return {
        "twilio_auth_token": "test_token_123",
        "memora_base_url": "https://memory.twilio.com/v1",
        "memory_service_sid": "MGtest123",
        "maestro_base_url": "https://maestro.twilio.com/v1",
        "conversation_service_sid": "IStest123",
        "twilio_account_sid": "ACtest123",
        "twilio_phone_number": "+15551234567",
    }


class TestVoiceChannel:
    """Test Voice Channel functionality."""

    def test_initialization(self) -> None:
        """Test Voice channel initialization."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        assert channel.taf == taf
        assert channel._active_websocket is None
        assert channel._current_conversation_id is None

    def test_get_channel_name(self) -> None:
        """Test get_channel_name returns 'voice'."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        assert channel.get_channel_name() == "voice"

    def test_handle_setup_message(self) -> None:
        """Test handling setup message initializes conversation."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL123"

        # Handle setup message
        setup_data = {"type": "setup"}
        channel.handle_message(setup_data)

        # Verify conversation was started
        assert "CALL123" in channel._conversations
        assert channel._conversations["CALL123"].profile_id == "default"
        assert channel._conversations["CALL123"].channel == "voice"

    def test_handle_prompt_message(self) -> None:
        """Test handling prompt message triggers memory retrieval."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL123"

        # Mock memory retrieval
        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[], summaries=[], sessions=[], meta=MemoryRetrievalMeta(queryTime=0)
            )
            mock_retrieve.return_value = empty_response

            # Handle prompt message
            prompt_data = {"type": "prompt", "voicePrompt": "Hello, I need help"}
            channel.handle_message(prompt_data)

            # Verify memory retrieval was called
            mock_retrieve.assert_called_once()

    def test_handle_interrupt_message(self) -> None:
        """Test handling interrupt message."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL123"

        # Handle interrupt message with full details
        interrupt_data = {
            "type": "interrupt",
            "utteranceUntilInterrupt": "Hello, I was saying...",
            "durationUntilInterruptMs": 1500,
        }
        channel.handle_message(interrupt_data)

    def test_handle_message_without_conversation_id(self) -> None:
        """Test handling message without conversation ID logs error."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # No conversation ID set
        channel._current_conversation_id = None

        # Should log error and return early
        setup_data = {"type": "setup"}
        channel.handle_message(setup_data)

        # No conversation should be created
        assert len(channel._conversations) == 0

    @pytest.mark.asyncio
    async def test_send_response(self) -> None:
        """Test sending voice response through websocket."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation
        channel._start_conversation("CALL123", "profile_test")

        # Mock websocket
        mock_websocket = AsyncMock()
        channel._active_websocket = mock_websocket

        # Send response without role
        await channel.send_response("CALL123", "Hello there")

        # Verify websocket.send_text was called
        mock_websocket.send_text.assert_called_once()

        # Verify message was added to conversation
        assert len(channel._conversations["CALL123"].messages) == 1
        assert channel._conversations["CALL123"].messages[0]["content"] == "Hello there"
        assert channel._conversations["CALL123"].messages[0]["role"] is None

        # Send response with role
        await channel.send_response("CALL123", "How can I help?", role="assistant")

        # Verify message with role was added
        assert len(channel._conversations["CALL123"].messages) == 2
        assert channel._conversations["CALL123"].messages[1]["content"] == "How can I help?"
        assert channel._conversations["CALL123"].messages[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_send_response_without_websocket(self) -> None:
        """Test sending response without active websocket logs error."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation
        channel._start_conversation("CALL123", "profile_test")

        # No active websocket
        channel._active_websocket = None

        # Should log error and return early
        await channel.send_response("CALL123", "Hello there")

        # Message should not be added
        assert len(channel._conversations["CALL123"].messages) == 0

    def test_end_conversation_cleanup(self) -> None:
        """Test ending conversation cleans up resources."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation
        channel._start_conversation("CALL123", "profile_test")
        channel._current_conversation_id = "CALL123"
        channel._active_websocket = MagicMock()

        # End conversation
        channel._end_conversation("CALL123")

        # Verify cleanup
        assert "CALL123" not in channel._conversations
        assert channel._active_websocket is None
        assert channel._current_conversation_id is None  # type: ignore[unreachable]

    def test_process_webhook_not_implemented(self) -> None:
        """Test that process_webhook is stubbed."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Should not raise
        channel.process_webhook({})

    def test_message_tracking_in_conversation(self) -> None:
        """Test that messages are tracked in conversation session."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID and start conversation
        channel._current_conversation_id = "CALL123"
        channel._start_conversation("CALL123", "profile_test")

        # Mock memory retrieval
        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[], summaries=[], sessions=[], meta=MemoryRetrievalMeta(queryTime=0)
            )
            mock_retrieve.return_value = empty_response

            # Handle prompt message
            prompt_data = {"type": "prompt", "voicePrompt": "First message"}
            channel.handle_message(prompt_data)

            # Verify message was added
            assert len(channel._conversations["CALL123"].messages) == 1
            assert channel._conversations["CALL123"].messages[0]["content"] == "First message"

            # Handle another prompt
            prompt_data = {"type": "prompt", "voicePrompt": "Second message"}
            channel.handle_message(prompt_data)

            # Verify both messages are tracked
            assert len(channel._conversations["CALL123"].messages) == 2

    @pytest.mark.asyncio
    async def test_memory_callback_integration(self) -> None:
        """Test memory callback is invoked with conversation context."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Callback to capture context
        captured_context = None
        captured_memories = None
        captured_user_message = None

        async def memory_callback(
            context: ConversationSession,
            memory_response: MemoryRetrievalResponse,
            user_message: str,
        ) -> None:
            nonlocal captured_context, captured_memories, captured_user_message
            captured_context = context
            captured_memories = memory_response
            captured_user_message = user_message

        taf.on_memory_ready(memory_callback)

        # Set current conversation ID and start conversation
        channel._current_conversation_id = "CALL123"
        channel._start_conversation("CALL123", "profile_test")

        # Mock memory retrieval
        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[], summaries=[], sessions=[], meta=MemoryRetrievalMeta(queryTime=0)
            )
            mock_retrieve.return_value = empty_response

            # Handle prompt message
            prompt_data = {"type": "prompt", "voicePrompt": "Test message"}
            channel.handle_message(prompt_data)

            # Give async callback time to execute
            import asyncio

            await asyncio.sleep(0.01)

            # Verify callback was invoked
            assert captured_context is not None
            assert captured_context.conversation_id == "CALL123"
            assert captured_context.profile_id == "profile_test"
            assert captured_context.channel == "voice"
            assert captured_memories is not None
            assert captured_user_message == "Test message"

    def test_handle_incoming_call(self) -> None:
        """Test handle_incoming_call generates valid TwiML."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Mock conversation creation
        with patch.object(taf.maestro_client, "create_conversation") as mock_create:
            mock_create.return_value = ConversationResponse(
                id="CONV123",
                account_id="ACtest123",
                service_id="IStest123",
            )

            # Generate TwiML
            twiml = channel.handle_incoming_call(
                websocket_url="wss://example.ngrok.io/ws", welcome_greeting="Welcome!"
            )

            # Verify TwiML contains expected elements
            assert '<?xml version="1.0" encoding="UTF-8"?>' in twiml
            assert "<Response>" in twiml
            assert "<Connect>" in twiml
            assert "<ConversationRelay" in twiml
            assert 'url="wss://example.ngrok.io/ws"' in twiml
            assert 'welcomeGreeting="Welcome!"' in twiml
            assert '<Parameter name="conversationId" value="CONV123" />' in twiml
            assert "</ConversationRelay>" in twiml
            assert "</Connect>" in twiml
            assert "</Response>" in twiml

    def test_handle_incoming_call_default_greeting(self) -> None:
        """Test handle_incoming_call uses default greeting."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Mock conversation creation
        with patch.object(taf.maestro_client, "create_conversation") as mock_create:
            mock_create.return_value = ConversationResponse(
                id="CONV456",
                account_id="ACtest123",
                service_id="IStest123",
            )

            # Generate TwiML without custom greeting
            twiml = channel.handle_incoming_call(websocket_url="wss://test.ngrok.io/ws")

            # Verify default greeting is used
            assert 'welcomeGreeting="Hello! How can I assist you today?"' in twiml

    def test_setup_with_custom_parameters_profile_id(self) -> None:
        """Test setup message extracts profile_id from custom parameters."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL123"

        # Handle setup with custom parameters including profile_id
        setup_data = {
            "type": "setup",
            "customParameters": {"conversationId": "CONV123", "profileId": "USER_PROFILE_789"},
        }
        channel.handle_message(setup_data)

        # Verify conversation was started with correct profile_id
        assert "CALL123" in channel._conversations
        assert channel._conversations["CALL123"].profile_id == "USER_PROFILE_789"

    def test_setup_without_custom_parameters_uses_default(self) -> None:
        """Test setup message uses 'default' profile_id when no custom parameters."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL456"

        # Handle setup without custom parameters
        setup_data = {"type": "setup"}
        channel.handle_message(setup_data)

        # Verify conversation was started with default profile_id
        assert "CALL456" in channel._conversations
        assert channel._conversations["CALL456"].profile_id == "default"

    def test_handle_message_invalid_data_logs_error(self) -> None:
        """Test handle_message logs error for invalid message data."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL789"

        # Handle message with invalid data (missing required fields for type validation)
        # This should trigger the exception handler in handle_message
        invalid_data = {"type": "setup", "sessionId": 12345}  # sessionId should be string

        # Should not raise exception, just log error
        channel.handle_message(invalid_data)

        # No conversation should be created due to validation error
        # (unless type matches and passes validation)

    def test_handle_message_unknown_type(self) -> None:
        """Test handle_message logs warning for unknown message type."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID
        channel._current_conversation_id = "CALL999"

        # Handle message with unknown type
        unknown_data = {"type": "unknown_type", "someField": "someValue"}

        # Should log warning but not raise exception
        channel.handle_message(unknown_data)

    def test_prompt_with_empty_voice_prompt(self) -> None:
        """Test handling prompt message with empty voice_prompt."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Set current conversation ID and start conversation
        channel._current_conversation_id = "CALL111"
        channel._start_conversation("CALL111", "profile_test")

        # Mock memory retrieval
        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[], summaries=[], sessions=[], meta=MemoryRetrievalMeta(queryTime=0)
            )
            mock_retrieve.return_value = empty_response

            # Handle prompt with None voicePrompt
            prompt_data = {"type": "prompt", "voicePrompt": None}
            channel.handle_message(prompt_data)

            # Verify message was added with empty string
            assert len(channel._conversations["CALL111"].messages) == 1
            assert channel._conversations["CALL111"].messages[0]["content"] == ""
