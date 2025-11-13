"""Tests for SMS Channel."""

import asyncio
from typing import Optional
from unittest.mock import MagicMock, patch

from taf import TAF
from taf.channels.sms import SMSChannel
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalMeta, MemoryRetrievalResponse


def get_test_config(with_memory=True) -> dict:
    """Get a valid test configuration."""
    config = {
        "twilio_auth_token": "test_token_123",
        "environment": "prod",
        "conversation_service_sid": "IStest123",
        "twilio_account_sid": "ACtest123",
        "twilio_phone_number": "+15551234567",
    }
    if with_memory:
        config["twilio_memory_config"] = {"memory_store_id": "MGtest123"}
    return config


class TestSMSChannel:
    """Test SMS Channel functionality."""

    def test_initialization(self) -> None:
        """Test SMS channel initialization."""
        with patch("taf.channels.sms.Client") as mock_client:
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            assert channel.taf == taf
            # Verify Twilio client was initialized
            mock_client.assert_called_once_with(
                taf.config.twilio_account_sid, taf.config.twilio_auth_token
            )

    def test_process_conversation_started(self) -> None:
        """Test processing onConversationAdded event."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Mock participant creation
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_participants_create = MagicMock()
            mock_client.conversations.v1.conversations.return_value.participants.create = (
                mock_participants_create
            )

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            webhook_data = {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Author": "+12345678901",
            }

            channel.process_webhook(webhook_data)

            # Verify conversation was started
            assert "CH123456" in channel._conversations
            assert channel._conversations["CH123456"].profile_id == "profile_test_123"

            # Verify participant was created
            mock_client.conversations.v1.conversations.assert_called_once_with("CH123456")
            mock_participants_create.assert_called_once()

    def test_process_message_auto_initialize(self) -> None:
        """Test processing message auto-initializes conversation if not started."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Callback to capture context
            captured_context = None
            captured_memories = None

            def message_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse],
            ) -> None:
                nonlocal captured_context, captured_memories
                captured_context = context
                captured_memories = memory_response

            taf.on_message_ready(message_callback)

            webhook_data = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "Body": "Hello, I need help",
                "Author": "+12345678901",
                "ProfileId": "profile_test_123",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_response = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    sessions=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_response

                channel.process_webhook(webhook_data)

                # Verify callback was invoked
                assert captured_context is not None
                assert captured_context.conversation_id == "CH123456"
                assert captured_context.profile_id == "profile_test_123"
                assert captured_context.channel == "sms"

    def test_process_message_with_existing_conversation(self) -> None:
        """Test processing message with pre-existing conversation."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Mock participant creation
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_participants_create = MagicMock()
            mock_client.conversations.v1.conversations.return_value.participants.create = (
                mock_participants_create
            )

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Start conversation first
            start_webhook = {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Author": "+12345678901",
            }

            channel.process_webhook(start_webhook)

            # Now process message
            message_webhook = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "Body": "Test message",
                "Author": "+12345678901",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_response = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    sessions=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_response

                channel.process_webhook(message_webhook)

                # Verify memory retrieval was called
                mock_retrieve.assert_called_once()

    def test_process_empty_message_ignored(self) -> None:
        """Test that empty messages are ignored."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            webhook_data = {
                "EventType": "onMessageAdded",
                "ConversationSid": "CH123456",
                "Body": "",
                "Author": "+12345678901",
                "ProfileId": "profile_test_123",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                channel.process_webhook(webhook_data)

                # Verify memory retrieval was NOT called
                mock_retrieve.assert_not_called()

    def test_process_conversation_ended(self) -> None:
        """Test processing onConversationRemoved event."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Mock participant creation
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_participants_create = MagicMock()
            mock_client.conversations.v1.conversations.return_value.participants.create = (
                mock_participants_create
            )

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Start conversation
            start_webhook = {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH123456",
                "ProfileId": "profile_test_123",
                "Author": "+12345678901",
            }

            channel.process_webhook(start_webhook)

            # End conversation
            end_webhook = {
                "EventType": "onConversationRemoved",
                "ConversationSid": "CH123456",
            }

            # Should not raise
            channel.process_webhook(end_webhook)

    def test_send_response_with_active_conversation(self) -> None:
        """Test sending response to active conversation."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Setup mock Twilio client
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_messages_create = MagicMock()
            mock_client.messages.create = mock_messages_create

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Mock list_participants to return a customer participant
            from taf.models.conversation import ParticipantAddress, ParticipantResponse

            mock_participant = ParticipantResponse(
                id="PA123",
                account_id="ACtest123",
                service_id="IStest123",
                conversation_id="CH123456",
                name="Test Customer",
                label="Customer",
                addresses=[ParticipantAddress(communication_type="SMS", value="+12345678901")],
            )

            with patch.object(
                taf.maestro_client, "list_participants", return_value=[mock_participant]
            ):
                # Start conversation
                start_webhook = {
                    "EventType": "onConversationAdded",
                    "ConversationSid": "CH123456",
                    "ProfileId": "profile_test_123",
                    "Author": "+12345678901",
                }

                channel.process_webhook(start_webhook)

                # Send response
                asyncio.run(channel.send_response("CH123456", "Test response"))

                # Verify Twilio messages API was called
                mock_messages_create.assert_called_once_with(
                    to="+12345678901",
                    from_=taf.config.twilio_phone_number,
                    body="Test response",
                )

    def test_send_response_to_unknown_conversation(self) -> None:
        """Test sending response to non-existent conversation logs error."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Should log error but not raise
            asyncio.run(channel.send_response("CH_UNKNOWN", "Test response"))

            # Verify Twilio messages API was NOT called
            mock_client.messages.create.assert_not_called()

    def test_multiple_concurrent_conversations(self) -> None:
        """Test handling multiple concurrent conversations."""
        with patch("taf.channels.sms.Client") as mock_client_class:
            # Mock participant creation
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            mock_participants_create = MagicMock()
            mock_client.conversations.v1.conversations.return_value.participants.create = (
                mock_participants_create
            )

            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            # Start first conversation
            channel.process_webhook(
                {
                    "EventType": "onConversationAdded",
                    "ConversationSid": "CH111",
                    "ProfileId": "profile_1",
                    "Author": "+11111111111",
                }
            )

            # Start second conversation
            channel.process_webhook(
                {
                    "EventType": "onConversationAdded",
                    "ConversationSid": "CH222",
                    "ProfileId": "profile_2",
                    "Author": "+12222222222",
                }
            )

            # Verify both conversations started successfully
            assert "CH111" in channel._conversations
            assert "CH222" in channel._conversations

            # End first conversation (should not raise)
            channel.process_webhook(
                {
                    "EventType": "onConversationRemoved",
                    "ConversationSid": "CH111",
                }
            )

            # Verify first conversation was removed
            assert "CH111" not in channel._conversations
            assert "CH222" in channel._conversations

    def test_ignores_unsupported_event_types(self) -> None:
        """Test that unsupported event types are ignored."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            webhook_data = {
                "EventType": "onParticipantAdded",
                "ConversationSid": "CH123456",
            }

            # Should not raise, just log debug message
            channel.process_webhook(webhook_data)
