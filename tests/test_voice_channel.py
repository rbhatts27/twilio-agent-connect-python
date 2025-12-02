"""Tests for Voice Channel."""

from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from taf import TAF
from taf.channels.voice import VoiceChannel
from taf.models.conversation import ConversationResponse, ParticipantResponse
from taf.models.memory import MemoryRetrievalResponse
from taf.models.session import ConversationSession
from taf.models.voice import InterruptMessage, PromptMessage, SetupMessage


def get_test_config() -> dict:
    """Get a valid test configuration."""
    return {
        "twilio_auth_token": "test_token_123",
        "environment": "prod",
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

    @pytest.mark.asyncio
    async def test_handle_setup_message(self) -> None:
        """Test handling setup message initializes conversation."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Create setup message
        setup_msg = SetupMessage(
            type="setup",
            conversationId="CALL123",
            customParameters={"conversationId": "CALL123"},
        )

        # Call handler directly
        await channel._handle_setup(setup_msg)

        # Verify conversation was started
        assert "CALL123" in channel._conversations
        assert channel._conversations["CALL123"].profile_id is None
        assert channel._conversations["CALL123"].channel == "voice"

    @pytest.mark.asyncio
    async def test_handle_prompt_message(self) -> None:
        """Test handling prompt message does NOT trigger memory retrieval (voice channel)."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Setup conversation first
        await channel._start_conversation("CALL123", "profile_test_123")

        # Create prompt message
        prompt_msg = PromptMessage(
            type="prompt",
            conversationId="CALL123",
            voicePrompt="Hello, I need help",
        )

        # Call handler directly
        await channel._handle_prompt("CALL123", prompt_msg)

        # Voice channel doesn't fetch memory - test passes if no exception raised

    @pytest.mark.asyncio
    async def test_handle_interrupt_message(self) -> None:
        """Test handling interrupt message."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Setup conversation first
        await channel._start_conversation("CALL123", None)

        # Create interrupt message
        interrupt_msg = InterruptMessage(
            type="interrupt",
            utteranceUntilInterrupt="Hello, I was saying...",
            durationUntilInterruptMs=1500,
        )

        # Call handler directly
        channel._handle_interrupt("CALL123", interrupt_msg)

        # Test passes if no exception is raised

    @pytest.mark.asyncio
    async def test_handle_message_without_conversation_id(self) -> None:
        """Test handling setup message without conversation ID logs error."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Create setup message without conversationId in custom parameters
        setup_msg = SetupMessage(type="setup")

        # Call handler directly
        await channel._handle_setup(setup_msg)

        # No conversation should be created
        assert len(channel._conversations) == 0

    @pytest.mark.asyncio
    async def test_send_response(self) -> None:
        """Test sending voice response through websocket."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation directly
        await channel._start_conversation("CALL123", "profile_test")

        # Mock websocket
        mock_websocket = AsyncMock()
        channel._active_websocket = mock_websocket

        # Send response without role
        await channel.send_response("CALL123", "Hello there")

        # Verify websocket.send_text was called once
        assert mock_websocket.send_text.call_count == 1

        # Send response with role
        await channel.send_response("CALL123", "How can I help?", role="assistant")

        # Verify websocket.send_text was called again
        assert mock_websocket.send_text.call_count == 2

    @pytest.mark.asyncio
    async def test_send_response_without_websocket(self) -> None:
        """Test sending response without active websocket logs error."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation directly
        await channel._start_conversation("CALL123", "profile_test")

        # No active websocket
        channel._active_websocket = None

        # Should log error and return early (no exception raised)
        await channel.send_response("CALL123", "Hello there")

    @pytest.mark.asyncio
    async def test_end_conversation_cleanup(self) -> None:
        """Test ending conversation cleans up resources."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Start conversation directly
        await channel._start_conversation("CALL123", "profile_test")
        channel._active_websocket = MagicMock()
        channel._current_conversation_id = "CALL123"

        # End conversation
        channel._end_conversation("CALL123")

        # Verify cleanup
        assert "CALL123" not in channel._conversations
        assert channel._active_websocket is None
        assert channel._current_conversation_id is None  # type: ignore[unreachable]

    @pytest.mark.asyncio
    async def test_process_webhook_not_implemented(self) -> None:
        """Test that process_webhook is stubbed."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Should not raise
        await channel.process_webhook({})

    @pytest.mark.asyncio
    async def test_message_callback_integration(self) -> None:
        """Test message callback is invoked with conversation context."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Callback to capture context
        captured_context = None
        captured_memories = None
        captured_user_message = None

        async def message_callback(
            user_message: str,
            context: ConversationSession,
            memory_response: Optional[MemoryRetrievalResponse],
        ) -> None:
            nonlocal captured_context, captured_memories, captured_user_message
            captured_context = context
            captured_memories = memory_response
            captured_user_message = user_message

        taf.on_message_ready(message_callback)

        # Setup conversation first
        await channel._start_conversation("CALL123", "profile_test")

        # Create and handle prompt message
        prompt_msg = PromptMessage(
            type="prompt",
            conversationId="CALL123",
            voicePrompt="Test message",
        )
        await channel._handle_prompt("CALL123", prompt_msg)

        # Verify callback was invoked
        assert captured_context is not None
        assert captured_context.conversation_id == "CALL123"
        assert captured_context.profile_id == "profile_test"
        assert captured_context.channel == "voice"
        # Voice channel doesn't fetch memory, so it should be None
        assert captured_memories is None
        assert captured_user_message == "Test message"

    @pytest.mark.asyncio
    async def test_handle_incoming_call(self) -> None:
        """Test handle_incoming_call generates valid TwiML."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Mock conversation creation and participant addition
        with (
            patch.object(
                taf.maestro_client, "create_conversation", new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                taf.maestro_client, "add_participant", new_callable=AsyncMock
            ) as mock_add_participant,
        ):
            mock_create.return_value = ConversationResponse(
                id="CONV123",
                account_id="ACtest123",
                service_id="IStest123",
            )
            mock_add_participant.return_value = ParticipantResponse(
                id="PART123",
                conversation_id="CONV123",
                account_id="ACtest123",
                service_id="IStest123",
                name="participant",
            )

            # Generate TwiML
            twiml = await channel.handle_incoming_call(
                websocket_url="wss://example.ngrok.io/ws",
                to_number="+15551234567",
                from_number="+15559999999",
                action_url="https://example.ngrok.io/flex_handoff",
                welcome_greeting="Welcome!",
            )

            # Verify TwiML contains expected elements
            assert '<?xml version="1.0" encoding="UTF-8"?>' in twiml
            assert "<Response>" in twiml
            assert '<Connect action="https://example.ngrok.io/flex_handoff">' in twiml
            assert "<ConversationRelay" in twiml
            assert 'url="wss://example.ngrok.io/ws"' in twiml
            assert 'welcomeGreeting="Welcome!"' in twiml
            assert '<Parameter name="conversationId" value="CONV123" />' in twiml
            assert "</ConversationRelay>" in twiml
            assert "</Connect>" in twiml
            assert "</Response>" in twiml

    @pytest.mark.asyncio
    async def test_handle_incoming_call_default_greeting(self) -> None:
        """Test handle_incoming_call uses default greeting."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Mock conversation creation and participant addition
        with (
            patch.object(
                taf.maestro_client, "create_conversation", new_callable=AsyncMock
            ) as mock_create,
            patch.object(
                taf.maestro_client, "add_participant", new_callable=AsyncMock
            ) as mock_add_participant,
        ):
            mock_create.return_value = ConversationResponse(
                id="CONV456",
                account_id="ACtest123",
                service_id="IStest123",
            )
            mock_add_participant.return_value = ParticipantResponse(
                id="PART456",
                conversation_id="CONV456",
                account_id="ACtest123",
                service_id="IStest123",
                name="participant",
            )

            # Generate TwiML without custom greeting
            twiml = await channel.handle_incoming_call(
                websocket_url="wss://test.ngrok.io/ws",
                to_number="+15551111111",
                from_number="+15559876543",
                action_url="https://example.ngrok.io/flex_handoff",
            )

            # Verify default greeting is used
            assert 'welcomeGreeting="Hello! How can I assist you today?"' in twiml

    @pytest.mark.asyncio
    async def test_setup_with_custom_parameters_profile_id(self) -> None:
        """Test setup message extracts profile_id from custom parameters."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Create setup message with profile_id
        setup_msg = SetupMessage(
            type="setup",
            conversationId="CONV123",
            customParameters={"conversationId": "CONV123", "profileId": "USER_PROFILE_789"},
        )

        # Call handler directly
        await channel._handle_setup(setup_msg)

        # Verify conversation was started with correct profile_id
        assert "CONV123" in channel._conversations
        assert channel._conversations["CONV123"].profile_id == "USER_PROFILE_789"

    @pytest.mark.asyncio
    async def test_setup_without_conversation_id_raises_error(self) -> None:
        """Test setup message logs error when conversationId missing from custom parameters."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Create setup message without conversationId in custom parameters
        setup_msg = SetupMessage(type="setup")

        # Call handler directly
        await channel._handle_setup(setup_msg)

        # Verify conversation was NOT started
        assert len(channel._conversations) == 0

    @pytest.mark.asyncio
    async def test_prompt_with_empty_voice_prompt(self) -> None:
        """Test handling prompt message with empty voice_prompt."""
        taf = TAF(get_test_config())
        channel = VoiceChannel(taf=taf)

        # Setup conversation first
        await channel._start_conversation("CALL111", "profile_test")

        # Create prompt message with None voicePrompt
        prompt_msg = PromptMessage(
            type="prompt",
            conversationId="CALL111",
            voicePrompt=None,
        )

        # Call handler directly
        await channel._handle_prompt("CALL111", prompt_msg)

        # Voice channel doesn't fetch memory - test passes if no exception raised
