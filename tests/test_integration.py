"""Integration tests for the complete TAF framework."""

import urllib.parse

import pytest

from taf import TAF, TAFConfig


class TestTAFIntegration:
    """Integration tests for complete TAF workflow."""

    def test_end_to_end_webhook_processing(self):
        """Test complete webhook processing workflow."""
        # Step 1: Create TAF instance
        config = TAFConfig()
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
        assert result == "I need help with my order"

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
        taf = TAF({})
        result = taf.process_message(event_dict)

        assert result == "Hello world"

    def test_multiple_providers_same_webhook(self):
        """Test processing same webhook with different AI providers."""
        webhook_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "Body": "Test message",
            "Author": "+12162622233",
        }

        # Test with OpenAI
        openai_taf = TAF({})
        openai_result = openai_taf.process_message(webhook_data)

        assert openai_result == "Test message"

    def test_webhook_filtering_workflow(self):
        """Test complete workflow for filtering different types of webhooks."""
        taf = TAF({})

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

            if test_case["webhook"]["EventType"] == "onMessageAdded":
                if test_case["should_process"]:
                    # Should return the message body
                    assert (
                        result is not None
                    ), f"Expected result for {test_case['name']}"
                    assert isinstance(
                        result, str
                    ), f"Expected string result for {test_case['name']}"
                else:
                    # Should return None for empty/whitespace messages
                    assert result is None, f"Expected None for {test_case['name']}"
            else:
                # Other event types return None
                assert (
                    result is None
                ), f"Expected None for unsupported event {test_case['name']}"

    def test_configuration_validation_workflow(self):
        """Test complete workflow with configuration validation."""
        # Valid configurations
        valid_configs = [
            {},
            TAFConfig(),
        ]

        for config in valid_configs:
            taf = TAF(config)
            assert taf.config.memora_auth_token is None

        # Configuration with extra fields should be allowed (ignored)
        flexible_config = {
            "extra_field": "extra_value",
            "memora_auth_token": "test_123",
        }
        taf = TAF(flexible_config)
        assert taf.config.memora_auth_token == "test_123"

        # Invalid configurations (wrong types)
        invalid_configs = [
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
        taf = TAF({})
        result = taf.process_message(real_webhook)

        # Verify complete processing
        assert result is not None
        assert "password" in result
        assert (
            result
            == "Hi, I'm having trouble with my account login. Can you help me reset my password?"
        )

    def test_batch_webhook_processing(self):
        """Test processing multiple webhooks in sequence."""
        taf = TAF({})

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

        # All should be processed and return message strings
        assert len(results) == 5
        assert all(isinstance(r, str) for r in results)
        assert all(r.startswith("Message ") for r in results)

        # Each message should be unique
        assert len(set(results)) == 5

    def test_error_recovery_workflow(self):
        """Test error handling in complete workflow."""
        taf = TAF({})

        # Process valid message first
        valid_webhook = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
            "Body": "Valid message",
            "Author": "+12162622233",
        }

        valid_result = taf.process_message(valid_webhook)
        assert valid_result == "Valid message"

        # Then try invalid webhook
        invalid_webhook = {"EventType": "onMessageAdded"}  # Missing required fields

        with pytest.raises(ValueError):  # Should raise ValueError
            taf.process_message(invalid_webhook)

        # TAF should still work after error
        another_valid_result = taf.process_message(valid_webhook)
        assert another_valid_result == "Valid message"
