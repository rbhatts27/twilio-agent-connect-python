"""Integration tests for the complete TAF framework."""

import urllib.parse

import pytest

from taf import TAF, ModelProvider, TAFConfig


class TestTAFIntegration:
    """Integration tests for complete TAF workflow."""

    def test_end_to_end_webhook_processing(self):
        """Test complete webhook processing workflow."""
        # Step 1: Create TAF instance
        config = TAFConfig(model_provider=ModelProvider.OPENAI)
        taf = TAF(config)

        # Step 2: Simulate webhook data
        webhook_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "Body": "I need help with my order",
            "Author": "+12162622233",
        }

        # Step 3: Process the webhook
        result = taf.process_message(webhook_data)

        # Step 4: Verify complete workflow
        assert result["processing"]["should_process"] is True
        assert result["processing"]["model_provider"] == "openai"
        assert result["event"]["body"] == "I need help with my order"
        assert (
            result["event"]["conversation_sid"] == "CHd151e6bcbe3643979a3f41f6d0da3b24"
        )

        # Step 5: Verify this would be sent to AI
        if result["processing"]["should_process"]:
            conversation_id = result["event"]["conversation_sid"]
            message = result["event"]["body"]
            model_provider = result["processing"]["model_provider"]

            # These would be used to call AI service
            assert conversation_id is not None
            assert message is not None
            assert model_provider is not None

    def test_url_encoded_webhook_processing(self):
        """Test processing URL-encoded webhook data like real Twilio webhooks."""
        # Real webhook payload format
        webhook_payload = (
            "EventType=onMessageAdded&"
            "ConversationSid=CHd151e6bcbe3643979a3f41f6d0da3b24&"
            "Body=Hello%20world&"
            "Author=%2B12162622233"
        )

        # Parse URL-encoded data
        parsed_data = urllib.parse.parse_qs(webhook_payload)
        event_dict = {k: v[0] for k, v in parsed_data.items()}

        # Process with TAF
        taf = TAF({"model_provider": "openai"})
        result = taf.process_message(event_dict)

        assert result["event"]["body"] == "Hello world"
        assert result["event"]["author"] == "+12162622233"
        assert result["processing"]["should_process"] is True

    def test_multiple_providers_same_webhook(self):
        """Test processing same webhook with different AI providers."""
        webhook_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "Body": "Test message",
            "Author": "+12162622233",
        }

        # Test with OpenAI
        openai_taf = TAF({"model_provider": "openai"})
        openai_result = openai_taf.process_message(webhook_data)

        assert openai_result["processing"]["model_provider"] == "openai"
        assert openai_result["processing"]["should_process"] is True

        # Both should process the same message consistently
        assert openai_result["event"]["body"] == "Test message"

    def test_webhook_filtering_workflow(self):
        """Test complete workflow for filtering different types of webhooks."""
        taf = TAF({"model_provider": "openai"})

        # Test cases with expected outcomes
        test_cases = [
            {
                "name": "Valid customer message",
                "webhook": {
                    "EventType": "onMessageAdded",
                    "ConversationSid": "CH123",
                    "Body": "I need help",
                    "Author": "+1234567890",
                },
                "should_process": True,
            },
            {
                "name": "Empty message",
                "webhook": {
                    "EventType": "onMessageAdded",
                    "ConversationSid": "CH123",
                    "Body": "",
                    "Author": "+1234567890",
                },
                "should_process": False,
            },
            {
                "name": "Whitespace message",
                "webhook": {
                    "EventType": "onMessageAdded",
                    "ConversationSid": "CH123",
                    "Body": "   \n  ",
                    "Author": "+1234567890",
                },
                "should_process": False,
            },
            {
                "name": "Non-message event",
                "webhook": {
                    "EventType": "onParticipantAdd",
                    "ConversationSid": "CH123",
                    "Body": "Hello",
                    "Author": "+1234567890",
                },
                "should_process": False,
            },
        ]

        for test_case in test_cases:
            result = taf.process_message(test_case["webhook"])
            assert (
                result["processing"]["should_process"] == test_case["should_process"]
            ), f"Failed for {test_case['name']}"

    def test_configuration_validation_workflow(self):
        """Test complete workflow with configuration validation."""
        # Valid configurations
        valid_configs = [
            {"model_provider": "openai"},
            TAFConfig(model_provider=ModelProvider.OPENAI),
        ]

        for config in valid_configs:
            taf = TAF(config)
            assert taf.get_model_provider() == "openai"

        # Invalid configurations
        invalid_configs = [
            {"model_provider": "invalid_provider"},
            "not_a_dict_or_config",
            123,
        ]

        for invalid_config in invalid_configs:
            with pytest.raises((ValueError, TypeError)):
                TAF(invalid_config)

    def test_real_world_webhook_scenario(self):
        """Test with real-world webhook scenario including all fields."""
        # Simulate complete Twilio webhook
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
        }

        # Process with TAF
        taf = TAF({"model_provider": "openai"})
        result = taf.process_message(real_webhook)

        # Verify complete processing
        assert result["processing"]["should_process"] is True
        assert result["event"]["is_message_event"] is True
        assert "password" in result["event"]["body"]
        assert result["event"]["author"] == "+12162622233"

        # This webhook should definitely be processed by AI
        assert result["processing"]["should_process"] is True

    def test_batch_webhook_processing(self):
        """Test processing multiple webhooks in sequence."""
        taf = TAF({"model_provider": "openai"})

        webhooks = [
            {
                "EventType": "onMessageAdded",
                "ConversationSid": f"CH{i:030d}",
                "Body": f"Message {i}",
                "Author": f"+1{i:010d}",
            }
            for i in range(5)
        ]

        results = []
        for webhook in webhooks:
            result = taf.process_message(webhook)
            results.append(result)

        # All should be processed
        assert len(results) == 5
        assert all(r["processing"]["should_process"] for r in results)

        # Each should have unique conversation ID
        conversation_ids = [r["event"]["conversation_sid"] for r in results]
        assert len(set(conversation_ids)) == 5

        # All should use same model provider
        providers = [r["processing"]["model_provider"] for r in results]
        assert all(p == "openai" for p in providers)

    def test_error_recovery_workflow(self):
        """Test error handling in complete workflow."""
        taf = TAF({"model_provider": "openai"})

        # Process valid message first
        valid_webhook = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "Body": "Valid message",
            "Author": "+12162622233",
        }

        valid_result = taf.process_message(valid_webhook)
        assert valid_result["processing"]["should_process"] is True

        # Then try invalid webhook
        invalid_webhook = {"EventType": "onMessageAdded"}  # Missing required fields

        with pytest.raises(ValueError):  # Should raise ValueError
            taf.process_message(invalid_webhook)

        # TAF should still work after error
        another_valid_result = taf.process_message(valid_webhook)
        assert another_valid_result["processing"]["should_process"] is True
