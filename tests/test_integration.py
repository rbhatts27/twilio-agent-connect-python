"""Integration tests for the complete TAF framework."""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.models.memory import MemoryRetrievalMeta, MemoryRetrievalResponse
from taf.models.session import ConversationSession


def get_test_config(with_memory=True):
    """Get a valid test configuration."""
    config = {
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


class TestTAFIntegration:
    """Integration tests for complete TAF workflow."""

    def test_configuration_validation_workflow(self):
        """Test complete workflow with configuration validation."""
        # Valid configurations
        valid_configs = [
            get_test_config(),
            TAFConfig(**get_test_config()),
        ]

        for config in valid_configs:
            taf = TAF(config)
            assert taf.config.twilio_auth_token == "test_token_123"

        # Configuration with extra fields should be allowed (ignored)
        flexible_config = get_test_config().copy()
        flexible_config["extra_field"] = "extra_value"
        taf = TAF(flexible_config)
        assert taf.config.twilio_auth_token == "test_token_123"

        # Invalid configurations (wrong types)
        invalid_configs = [
            "not_a_dict_or_config",
            123,
        ]

        for invalid_config in invalid_configs:
            with pytest.raises((ValueError, TypeError)):
                TAF(invalid_config)

    def test_sms_channel_end_to_end_workflow(self):
        """Test complete SMS channel workflow from webhook to callback."""
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

            # Track callback invocations
            callback_invoked = False
            received_context = None
            received_memories = None

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_invoked, received_context, received_memories
                callback_invoked = True
                received_context = context
                received_memories = memory_response

            taf.on_message_ready(message_ready_callback)

            # Simulate conversation.created webhook
            conversation_created = {
                "EventType": "conversation.created",
                "ConversationId": "CH123456",
                "ConversationStatus": "ACTIVE",
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            channel.process_webhook(conversation_created)

            # Simulate participant.added webhook (CUSTOMER with profile)
            participant_added = {
                "EventType": "participant.added",
                "ConversationId": "CH123456",
                "ParticipantId": "MB123",
                "ParticipantType": "CUSTOMER",
                "ProfileId": "profile_test_123",
                "ParticipantName": "+12345678901",
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }

            channel.process_webhook(participant_added)

            # Verify conversation was initialized with profile
            assert "CH123456" in channel._conversations
            assert channel._conversations["CH123456"].profile_id == "profile_test_123"

            # Simulate communication.created webhook (incoming message)
            message_webhook = {
                "EventType": "communication.created",
                "ConversationId": "CH123456",
                "CommunicationId": "IM123",
                "AuthorParticipantId": "MB123",
                "AuthorAddress": "+12345678901",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"Hello, I need help with my order"}',
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

                # Verify callback was invoked with correct data
                assert callback_invoked
                assert received_context is not None
                assert received_context.conversation_id == "CH123456"
                assert received_context.profile_id == "profile_test_123"
                assert received_context.channel == "sms"
                assert received_memories == empty_response
                assert len(received_memories.observations) == 0
                assert len(received_memories.summaries) == 0

    def test_sms_channel_auto_initialize_conversation(self):
        """Test SMS channel auto-initializes conversation on first message."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            callback_invoked = False

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_invoked
                callback_invoked = True

            taf.on_message_ready(message_ready_callback)

            # Send message without explicit conversation start (auto-initialize)
            message_webhook = {
                "EventType": "communication.created",
                "ConversationId": "CH999999",
                "CommunicationId": "IM999",
                "AuthorParticipantId": "MB999",
                "AuthorAddress": "+19999999999",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"First message without conversation start"}',
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_response = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_response

                channel.process_webhook(message_webhook)

                # Verify conversation was auto-initialized
                assert "CH999999" in channel._conversations
                assert callback_invoked

    def test_sms_channel_filters_empty_messages(self):
        """Test SMS channel ignores empty/whitespace messages."""
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

            callback_invoked = False

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_invoked
                callback_invoked = True

            taf.on_message_ready(message_ready_callback)

            # Initialize conversation
            channel.process_webhook(
                {
                    "EventType": "conversation.created",
                    "ConversationId": "CH111",
                    "ConversationStatus": "ACTIVE",
                    "Timestamp": "2025-11-18T00:00:00.000Z",
                }
            )

            # Test empty message
            empty_message = {
                "EventType": "communication.created",
                "ConversationId": "CH111",
                "CommunicationId": "IM111a",
                "AuthorParticipantId": "MB111",
                "AuthorAddress": "+11111111111",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":""}',
                "Timestamp": "2025-11-18T00:00:01.000Z",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                channel.process_webhook(empty_message)
                mock_retrieve.assert_not_called()
                assert not callback_invoked

            # Test whitespace message
            whitespace_message = {
                "EventType": "communication.created",
                "ConversationId": "CH111",
                "CommunicationId": "IM111b",
                "AuthorParticipantId": "MB111",
                "AuthorAddress": "+11111111111",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"   \\n\\t   "}',
                "Timestamp": "2025-11-18T00:00:02.000Z",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                channel.process_webhook(whitespace_message)
                mock_retrieve.assert_not_called()
                assert not callback_invoked

    def test_sms_channel_conversation_cleanup(self):
        """Test SMS channel cleans up conversation state properly."""
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
            channel.process_webhook(
                {
                    "EventType": "conversation.created",
                    "ConversationId": "CH222",
                    "ConversationStatus": "ACTIVE",
                    "Timestamp": "2025-11-18T00:00:00.000Z",
                }
            )

            assert "CH222" in channel._conversations

            # End conversation (status changed to CLOSED)
            channel.process_webhook(
                {
                    "EventType": "conversation.updated",
                    "ConversationId": "CH222",
                    "ConversationStatus": "CLOSED",
                    "Timestamp": "2025-11-18T00:10:00.000Z",
                }
            )

            assert "CH222" not in channel._conversations

    def test_sms_channel_multiple_concurrent_conversations(self):
        """Test SMS channel handles multiple concurrent conversations."""
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

            callback_count = 0
            conversation_ids = set()

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_count
                callback_count += 1
                conversation_ids.add(context.conversation_id)

            taf.on_message_ready(message_ready_callback)

            # Start multiple conversations
            for i in range(3):
                conv_id = f"CH{i:06d}"
                channel.process_webhook(
                    {
                        "EventType": "conversation.created",
                        "ConversationId": conv_id,
                        "ConversationStatus": "ACTIVE",
                        "Timestamp": f"2025-11-18T00:00:{i:02d}.000Z",
                    }
                )

            # Send messages to each conversation
            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_response = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_response

                for i in range(3):
                    conv_id = f"CH{i:06d}"
                    channel.process_webhook(
                        {
                            "EventType": "communication.created",
                            "ConversationId": conv_id,
                            "CommunicationId": f"IM{i:06d}",
                            "AuthorParticipantId": f"MB{i:06d}",
                            "AuthorAddress": f"+1{i:010d}",
                            "AuthorChannel": "SMS",
                            "Body": f'{{"type":"TEXT","text":"Message {i}"}}',
                            "Timestamp": f"2025-11-18T00:01:{i:02d}.000Z",
                        }
                    )

            # Verify all callbacks were invoked
            assert callback_count == 3
            assert len(conversation_ids) == 3

    def test_sms_channel_real_world_webhook_scenario(self):
        """Test SMS channel with real-world webhook data including all fields."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            callback_invoked = False
            received_context = None

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_invoked, received_context
                callback_invoked = True
                received_context = context

            taf.on_message_ready(message_ready_callback)

            # Simulate real Twilio webhook with ConversationEvent format
            real_webhook = {
                "EventType": "communication.created",
                "Timestamp": "2025-09-17T22:23:11.350Z",
                "AccountId": "ACa0cec02523bd4da792b4bff42b77fc22",
                "ConfigurationId": "IS21622ffdbc4947a4a0c1abaa77dfd024",
                "ConversationId": "CHd151e6bcbe3643979a3f41f6d0da3b24",
                "AuthorParticipantId": "MB723da60623f74438acee5baafbd438f0",
                "CommunicationId": "IM40cb38d6045f4da195651b3e29cca1dc",
                "Body": (
                    '{"type":"TEXT","text":"Hi, I\'m having trouble with my account login. '
                    'Can you help me reset my password?"}'
                ),
                "AuthorAddress": "+12162622233",
                "AuthorChannel": "SMS",
                "Language": "en-US",
            }

            with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
                empty_response = MemoryRetrievalResponse(
                    observations=[],
                    summaries=[],
                    meta=MemoryRetrievalMeta(queryTime=0),
                )
                mock_retrieve.return_value = empty_response

                channel.process_webhook(real_webhook)

                # Verify processing completed
                assert callback_invoked
                assert received_context is not None
                assert received_context.conversation_id == "CHd151e6bcbe3643979a3f41f6d0da3b24"
                # No profile_id in this webhook (auto-initialized without profile)
                assert received_context.profile_id is None
                assert received_context.channel == "sms"

    def test_sms_channel_missing_profile_id_handling(self):
        """Test SMS channel raises ValueError when profile_id is missing."""
        with patch("taf.channels.sms.Client"):
            taf = TAF(get_test_config())
            channel = SMSChannel(taf)

            callback_invoked = False

            def message_ready_callback(
                user_message: str,
                context: ConversationSession,
                memory_response: Optional[MemoryRetrievalResponse] = None,
            ):
                nonlocal callback_invoked
                callback_invoked = True

            taf.on_message_ready(message_ready_callback)

            # Message without profile_id (using new event format)
            message_webhook = {
                "EventType": "communication.created",
                "ConversationId": "CH777",
                "CommunicationId": "IM777",
                "AuthorParticipantId": "MB777",
                "AuthorAddress": "+17777777777",
                "AuthorChannel": "SMS",
                "Body": '{"type":"TEXT","text":"Message without profile"}',
                "Timestamp": "2025-11-18T00:00:00.000Z",
            }

            # Verify that processing webhook without profile_id doesn't propagate
            # an exception to the caller. The conversation is auto-initialized with
            # None profile_id, which will cause retrieve_memory to raise ValueError
            # internally if memory is enabled; otherwise, no exception is raised.
            # In both cases, the exception (if any) is handled internally and the
            # callback is still invoked.
            channel.process_webhook(message_webhook)

            # Callback should be invoked despite the memory retrieval error
            # (memory retrieval failure doesn't prevent message processing)
            assert callback_invoked
            # Verify conversation was auto-initialized despite the error
            assert "CH777" in channel._conversations
