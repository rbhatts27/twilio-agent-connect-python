"""Tests for SMS Channel."""

from unittest.mock import patch

from taf import TAF
from taf.channels.sms import SMSChannel
from taf.context.memory import TwilioMemory
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


class TestSMSChannel:
    """Test SMS Channel functionality."""

    def test_initialization(self) -> None:
        """Test SMS channel initialization."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        assert channel.taf == taf

    def test_process_conversation_started(self) -> None:
        """Test processing onConversationAdded event."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        webhook_data = {
            "eventType": "onConversationAdded",
            "conversationId": "CH123456",
            "participantProfileId": "profile_test_123",
        }

        channel.process_webhook(webhook_data)

        # Verify conversation was started
        assert "CH123456" in channel._conversations
        assert channel._conversations["CH123456"].profile_id == "profile_test_123"

    def test_process_message_auto_initialize(self) -> None:
        """Test processing message auto-initializes conversation if not started."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Callback to capture context
        captured_context = None
        captured_memories = None

        def memory_callback(context: ConversationSession, memories: list[TwilioMemory]) -> None:
            nonlocal captured_context, captured_memories
            captured_context = context
            captured_memories = memories

        taf.on_memory_ready(memory_callback)

        webhook_data = {
            "eventType": "onMessageAdded",
            "conversationId": "CH123456",
            "communicationMessageBody": "Hello, I need help",
            "communicationMessageAuthor": "+12345678901",
            "participantProfileId": "profile_test_123",
            "communicationId": "IM123456",
            "communicationChannel": "sms",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            channel.process_webhook(webhook_data)

            # Verify callback was invoked
            assert captured_context is not None
            assert captured_context.conversation_id == "CH123456"
            assert captured_context.profile_id == "profile_test_123"
            assert captured_context.channel == "sms"

    def test_process_message_with_existing_conversation(self) -> None:
        """Test processing message with pre-existing conversation."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start conversation first
        start_webhook = {
            "eventType": "onConversationAdded",
            "conversationId": "CH123456",
            "participantProfileId": "profile_test_123",
        }

        channel.process_webhook(start_webhook)

        # Now process message
        message_webhook = {
            "eventType": "onMessageAdded",
            "conversationId": "CH123456",
            "communicationMessageBody": "Test message",
            "communicationMessageAuthor": "+12345678901",
            "communicationId": "IM123456",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            channel.process_webhook(message_webhook)

            # Verify memory retrieval was called
            mock_retrieve.assert_called_once()

    def test_process_empty_message_ignored(self) -> None:
        """Test that empty messages are ignored."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        webhook_data = {
            "eventType": "onMessageAdded",
            "conversationId": "CH123456",
            "communicationMessageBody": "",
            "communicationMessageAuthor": "+12345678901",
            "participantProfileId": "profile_test_123",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            channel.process_webhook(webhook_data)

            # Verify memory retrieval was NOT called
            mock_retrieve.assert_not_called()

    def test_process_conversation_ended(self) -> None:
        """Test processing onConversationRemoved event."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start conversation
        start_webhook = {
            "eventType": "onConversationAdded",
            "conversationId": "CH123456",
            "participantProfileId": "profile_test_123",
        }

        channel.process_webhook(start_webhook)

        # End conversation
        end_webhook = {
            "eventType": "onConversationRemoved",
            "conversationId": "CH123456",
        }

        # Should not raise
        channel.process_webhook(end_webhook)

    def test_send_response_with_active_conversation(self) -> None:
        """Test sending response to active conversation."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start conversation
        start_webhook = {
            "eventType": "onConversationAdded",
            "conversationId": "CH123456",
            "participantProfileId": "profile_test_123",
        }

        channel.process_webhook(start_webhook)

        # Send response (should not raise)
        channel.send_response("CH123456", "Test response")

    def test_send_response_to_unknown_conversation(self) -> None:
        """Test sending response to non-existent conversation logs error."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Should log error but not raise
        channel.send_response("CH_UNKNOWN", "Test response")

    def test_multiple_concurrent_conversations(self) -> None:
        """Test handling multiple concurrent conversations."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start first conversation
        channel.process_webhook(
            {
                "eventType": "onConversationAdded",
                "conversationId": "CH111",
                "participantProfileId": "profile_1",
            }
        )

        # Start second conversation
        channel.process_webhook(
            {
                "eventType": "onConversationAdded",
                "conversationId": "CH222",
                "participantProfileId": "profile_2",
            }
        )

        # Verify both conversations started successfully
        assert "CH111" in channel._conversations
        assert "CH222" in channel._conversations

        # End first conversation (should not raise)
        channel.process_webhook(
            {
                "eventType": "onConversationRemoved",
                "conversationId": "CH111",
            }
        )

        # Verify first conversation was removed
        assert "CH111" not in channel._conversations
        assert "CH222" in channel._conversations

    def test_ignores_unsupported_event_types(self) -> None:
        """Test that unsupported event types are ignored."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        webhook_data = {
            "eventType": "onParticipantAdded",
            "conversationId": "CH123456",
        }

        # Should not raise, just log debug message
        channel.process_webhook(webhook_data)
