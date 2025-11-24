"""Tests for SMS Channel."""

import asyncio
from typing import Any, Optional
from unittest.mock import patch

from taf import TAF
from taf.channels.sms import SMSChannel
from taf.models.memory import MemoryRetrievalMeta, MemoryRetrievalResponse
from taf.models.session import ConversationSession


def get_test_config(with_memory: bool = True) -> dict[str, Any]:
    """Get a valid test configuration."""
    config: dict[str, Any] = {
        "twilio_auth_token": "test_token_123",
        "environment": "prod",
        "conversation_service_sid": "IStest123",
        "twilio_account_sid": "ACtest123",
        "twilio_phone_number": "+15551234567",
    }
    if with_memory:
        config["twilio_memory_config"] = {
            "memory_store_id": "MGtest123",
            "api_key": "test_api_key",
            "api_token": "test_api_token",
        }
    return config


class TestSMSChannel:
    """Test SMS Channel functionality."""

    def test_initialization(self) -> None:
        """Test SMS channel initialization."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        assert channel.taf == taf

    def test_process_conversation_started(self) -> None:
        """Test processing conversation.created and participant.added events."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Process conversation.created
        conversation_webhook = {
            "EventType": "conversation.created",
            "ConversationId": "CH123456",
            "ConversationStatus": "ACTIVE",
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }
        channel.process_webhook(conversation_webhook)

        # Process participant.added
        participant_webhook = {
            "EventType": "participant.added",
            "ConversationId": "CH123456",
            "ParticipantId": "MB123",
            "ParticipantType": "CUSTOMER",
            "ProfileId": "profile_test_123",
            "ParticipantName": "+12345678901",
            "Timestamp": "2025-11-18T00:00:01.000Z",
        }
        channel.process_webhook(participant_webhook)

        # Verify conversation was started with profile
        assert "CH123456" in channel._conversations
        assert channel._conversations["CH123456"].profile_id == "profile_test_123"

    def test_process_message_auto_initialize(self) -> None:
        """Test processing message auto-initializes conversation if not started."""
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
            "EventType": "communication.created",
            "ConversationId": "CH123456",
            "CommunicationId": "IM123",
            "AuthorParticipantId": "MB123",
            "AuthorAddress": "+12345678901",
            "AuthorChannel": "SMS",
            "Body": '{"type":"TEXT","text":"Hello, I need help"}',
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
            mock_retrieve.return_value = empty_response

            channel.process_webhook(webhook_data)

            # Verify callback was invoked
            assert captured_context is not None
            assert captured_context.conversation_id == "CH123456"
            # No profile_id since message auto-initialized without participant.added event
            assert captured_context.profile_id is None
            assert captured_context.channel == "sms"

    def test_process_message_with_existing_conversation(self) -> None:
        """Test processing message with pre-existing conversation."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start conversation first
        conversation_webhook = {
            "EventType": "conversation.created",
            "ConversationId": "CH123456",
            "ConversationStatus": "ACTIVE",
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }
        channel.process_webhook(conversation_webhook)

        participant_webhook = {
            "EventType": "participant.added",
            "ConversationId": "CH123456",
            "ParticipantId": "MB123",
            "ParticipantType": "CUSTOMER",
            "ProfileId": "profile_test_123",
            "ParticipantName": "+12345678901",
            "Timestamp": "2025-11-18T00:00:01.000Z",
        }
        channel.process_webhook(participant_webhook)

        # Now process message
        message_webhook = {
            "EventType": "communication.created",
            "ConversationId": "CH123456",
            "CommunicationId": "IM123",
            "AuthorParticipantId": "MB123",
            "AuthorAddress": "+12345678901",
            "AuthorChannel": "SMS",
            "Body": '{"type":"TEXT","text":"Test message"}',
            "Timestamp": "2025-11-18T00:00:02.000Z",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            empty_response = MemoryRetrievalResponse(
                observations=[],
                summaries=[],
                meta=MemoryRetrievalMeta(queryTime=0),
            )
            mock_retrieve.return_value = empty_response

            channel.process_webhook(message_webhook)

            # Verify memory retrieval was called
            mock_retrieve.assert_called_once()

    def test_process_empty_message_ignored(self) -> None:
        """Test that empty messages are ignored."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        webhook_data = {
            "EventType": "communication.created",
            "ConversationId": "CH123456",
            "CommunicationId": "IM123",
            "AuthorParticipantId": "MB123",
            "AuthorAddress": "+12345678901",
            "AuthorChannel": "SMS",
            "Body": '{"type":"TEXT","text":""}',
            "Timestamp": "2025-11-18T00:00:00.000Z",
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
            "EventType": "conversation.created",
            "ConversationId": "CH123456",
            "ConversationStatus": "ACTIVE",
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }
        channel.process_webhook(start_webhook)

        # End conversation (status changed to CLOSED)
        end_webhook = {
            "EventType": "conversation.updated",
            "ConversationId": "CH123456",
            "ConversationStatus": "CLOSED",
            "Timestamp": "2025-11-18T00:10:00.000Z",
        }

        # Should not raise
        channel.process_webhook(end_webhook)

    def test_send_response_with_active_conversation(self) -> None:
        """Test sending response to active conversation."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Mock list_participants to return customer participant with matching profile_id
        from taf.models.conversation import ParticipantResponse

        mock_customer_participant = ParticipantResponse(
            **{  # type: ignore[arg-type]
                "id": "PA_CUSTOMER",
                "accountId": "ACtest123",
                "serviceId": "IStest123",
                "conversationId": "CH123456",
                "name": "Test Customer",
                "type": "CUSTOMER",
                "profileId": "profile_test_123",  # Matching profile_id
                "addresses": [{"channel": "SMS", "address": "+12345678901"}],
            }
        )

        # Start conversation with profile_id
        start_webhook = {
            "EventType": "conversation.created",
            "ConversationId": "CH123456",
            "ConversationStatus": "ACTIVE",
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }
        channel.process_webhook(start_webhook)

        # Add participant to set profile_id
        participant_webhook = {
            "EventType": "participant.added",
            "ConversationId": "CH123456",
            "ParticipantId": "PA_CUSTOMER",
            "ParticipantType": "CUSTOMER",
            "ProfileId": "profile_test_123",
            "ParticipantName": "+12345678901",
            "Timestamp": "2025-11-18T00:00:01.000Z",
        }
        channel.process_webhook(participant_webhook)

        with (
            patch.object(
                taf.maestro_client,
                "list_participants",
                return_value=[mock_customer_participant],
            ),
            patch.object(channel.twilio.messages, "create") as mock_twilio_send,
        ):
            # Send response
            asyncio.run(channel.send_response("CH123456", "Test response"))

            # Verify Twilio message was sent to the correct recipient
            mock_twilio_send.assert_called_once_with(
                to="+12345678901",
                from_=taf.config.twilio_phone_number,
                body="Test response",
            )

    def test_send_response_to_unknown_conversation(self) -> None:
        """Test sending response to non-existent conversation logs error."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Should log error but not raise
        asyncio.run(channel.send_response("CH_UNKNOWN", "Test response"))

    def test_multiple_concurrent_conversations(self) -> None:
        """Test handling multiple concurrent conversations."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start first conversation
        channel.process_webhook(
            {
                "EventType": "conversation.created",
                "ConversationId": "CH111",
                "ConversationStatus": "ACTIVE",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }
        )

        # Start second conversation
        channel.process_webhook(
            {
                "EventType": "conversation.created",
                "ConversationId": "CH222",
                "ConversationStatus": "ACTIVE",
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }
        )

        # Verify both conversations started successfully
        assert "CH111" in channel._conversations
        assert "CH222" in channel._conversations

        # End first conversation (should not raise)
        channel.process_webhook(
            {
                "EventType": "conversation.updated",
                "ConversationId": "CH111",
                "ConversationStatus": "CLOSED",
                "Timestamp": "2025-11-18T00:10:00.000Z",
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
            "EventType": "some.unsupported.event",
            "ConversationId": "CH123456",
            "Timestamp": "2025-11-18T00:00:00.000Z",
        }

        # Should not raise, just log debug message
        channel.process_webhook(webhook_data)
