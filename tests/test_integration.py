"""Integration tests for the complete TAF framework."""

from typing import List
from unittest.mock import patch

import pytest

from taf import TAF, TAFConfig
from taf.channels.sms import SMSChannel
from taf.context.memora import MemoraMemory
from taf.core.context import ConversationContext


def get_test_config():
    """Get a valid test configuration."""
    return {
        "twilio_auth_token": "test_token_123",
        "memora_base_url": "https://memory.twilio.com/v1",
        "memory_service_sid": "MGtest123",
        "maestro_base_url": "https://maestro.twilio.com/v1",
        "conversation_service_sid": "IStest123",
        "twilio_account_sid": "ACtest123",
    }


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
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Track callback invocations
        callback_invoked = False
        received_context = None
        received_memories = None

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_invoked, received_context, received_memories
            callback_invoked = True
            received_context = context
            received_memories = memories

        taf.on_memory_ready(memory_ready_callback)

        # Simulate conversation started webhook
        conversation_started = {
            "EventType": "onConversationAdded",
            "ConversationSid": "CH123456",
            "profile_id": "profile_test_123",
            "Author": "+12345678901",
        }

        channel.process_webhook(conversation_started)

        # Verify conversation was initialized
        assert "CH123456" in channel._conversations
        assert channel._conversations["CH123456"].profile_id == "profile_test_123"

        # Simulate message webhook
        message_webhook = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH123456",
            "Body": "Hello, I need help with my order",
            "Author": "+12345678901",
            "MessageSid": "IM123456",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            channel.process_webhook(message_webhook)

            # Verify memory retrieval was called
            mock_retrieve.assert_called_once()

            # Verify callback was invoked with correct data
            assert callback_invoked
            assert received_context is not None
            assert received_context.conversation_id == "CH123456"
            assert received_context.profile_id == "profile_test_123"
            assert received_context.channel == "sms"
            assert received_memories == []

    def test_sms_channel_auto_initialize_conversation(self):
        """Test SMS channel auto-initializes conversation on first message."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        callback_invoked = False

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_invoked
            callback_invoked = True

        taf.on_memory_ready(memory_ready_callback)

        # Send message without explicit conversation start
        message_webhook = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH999999",
            "Body": "First message without conversation start",
            "Author": "+19999999999",
            "profile_id": "profile_999",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            channel.process_webhook(message_webhook)

            # Verify conversation was auto-initialized
            assert "CH999999" in channel._conversations
            assert callback_invoked

    def test_sms_channel_filters_empty_messages(self):
        """Test SMS channel ignores empty/whitespace messages."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        callback_invoked = False

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_invoked
            callback_invoked = True

        taf.on_memory_ready(memory_ready_callback)

        # Initialize conversation
        channel.process_webhook(
            {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH111",
                "profile_id": "profile_111",
                "Author": "+11111111111",
            }
        )

        # Test empty message
        empty_message = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH111",
            "Body": "",
            "Author": "+11111111111",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            channel.process_webhook(empty_message)
            mock_retrieve.assert_not_called()
            assert not callback_invoked

        # Test whitespace message
        whitespace_message = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH111",
            "Body": "   \n\t   ",
            "Author": "+11111111111",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            channel.process_webhook(whitespace_message)
            mock_retrieve.assert_not_called()
            assert not callback_invoked

    def test_sms_channel_conversation_cleanup(self):
        """Test SMS channel cleans up conversation state properly."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        # Start conversation
        channel.process_webhook(
            {
                "EventType": "onConversationAdded",
                "ConversationSid": "CH222",
                "profile_id": "profile_222",
                "Author": "+22222222222",
            }
        )

        assert "CH222" in channel._conversations

        # End conversation
        channel.process_webhook(
            {"EventType": "onConversationRemoved", "ConversationSid": "CH222"}
        )

        assert "CH222" not in channel._conversations

    def test_sms_channel_multiple_concurrent_conversations(self):
        """Test SMS channel handles multiple concurrent conversations."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        callback_count = 0
        conversation_ids = set()

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_count
            callback_count += 1
            conversation_ids.add(context.conversation_id)

        taf.on_memory_ready(memory_ready_callback)

        # Start multiple conversations
        for i in range(3):
            conv_id = f"CH{i:06d}"
            channel.process_webhook(
                {
                    "EventType": "onConversationAdded",
                    "ConversationSid": conv_id,
                    "profile_id": f"profile_{i}",
                    "Author": f"+1{i:010d}",
                }
            )

        # Send messages to each conversation
        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            for i in range(3):
                conv_id = f"CH{i:06d}"
                channel.process_webhook(
                    {
                        "EventType": "onMessageAdded",
                        "ConversationSid": conv_id,
                        "Body": f"Message {i}",
                        "Author": f"+1{i:010d}",
                    }
                )

        # Verify all callbacks were invoked
        assert callback_count == 3
        assert len(conversation_ids) == 3

    def test_sms_channel_real_world_webhook_scenario(self):
        """Test SMS channel with real-world webhook data including all fields."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        callback_invoked = False
        received_context = None

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_invoked, received_context
            callback_invoked = True
            received_context = context

        taf.on_memory_ready(memory_ready_callback)

        # Simulate real Twilio webhook with all fields
        real_webhook = {
            "MessagingServiceSid": "MG3675a614bcfcfb1921727b0138617cdf",
            "EventType": "onMessageAdded",
            "Attributes": "{}",
            "DateCreated": "2025-09-17T22:23:11.350Z",
            "Index": "8",
            "ChatServiceSid": "IS21622ffdbc4947a4a0c1abaa77dfd024",
            "MessageSid": "IM40cb38d6045f4da195651b3e29cca1dc",
            "AccountSid": "ACa0cec02523bd4da792b4bff42b77fc22",
            "Source": "SMS",
            "RetryCount": "0",
            "Author": "+12162622233",
            "ParticipantSid": "MB723da60623f74438acee5baafbd438f0",
            "Body": "Hi, I'm having trouble with my account login. Can you help me reset my password?",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "profile_id": "profile_realworld_123",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            mock_retrieve.return_value = []

            channel.process_webhook(real_webhook)

            # Verify processing completed
            assert callback_invoked
            assert received_context is not None
            assert (
                received_context.conversation_id == "CHd151e6bcbe3643979a3f41f6d0da3b24"
            )
            assert received_context.profile_id == "profile_realworld_123"
            assert received_context.channel == "sms"

    def test_sms_channel_missing_profile_id_handling(self):
        """Test SMS channel handles missing profile_id gracefully."""
        taf = TAF(get_test_config())
        channel = SMSChannel(taf)

        callback_invoked = False

        def memory_ready_callback(
            context: ConversationContext, memories: List[MemoraMemory]
        ):
            nonlocal callback_invoked
            callback_invoked = True

        taf.on_memory_ready(memory_ready_callback)

        # Message without profile_id
        message_webhook = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH777",
            "Body": "Message without profile",
            "Author": "+17777777777",
        }

        with patch.object(taf.memora_client, "retrieve_memory") as mock_retrieve:
            channel.process_webhook(message_webhook)

            # Verify memory retrieval was NOT called due to missing profile_id
            mock_retrieve.assert_not_called()
            assert not callback_invoked
            # Verify conversation was not initialized
            assert "CH777" not in channel._conversations
