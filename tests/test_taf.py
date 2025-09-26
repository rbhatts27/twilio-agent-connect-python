"""Tests for TAF core class."""

import pytest
from pydantic import ValidationError

from taf import TAF, TAFConfig


class TestTAF:
    """Test TAF core class."""

    def test_init_with_config_dict(self):
        """Test TAF initialization with configuration dictionary."""
        config_dict = {"memora_auth_token": "test_token_123"}
        taf = TAF(config_dict)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.memora_auth_token == "test_token_123"

    def test_init_with_config_object(self):
        """Test TAF initialization with TAFConfig object."""
        config = TAFConfig(memora_auth_token="test_token_123")
        taf = TAF(config)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.memora_auth_token == "test_token_123"

    def test_init_with_empty_config_dict(self):
        """Test TAF initialization with empty configuration dictionary."""
        config_dict = {}
        taf = TAF(config_dict)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.memora_auth_token is None

    def test_init_with_invalid_config_type(self):
        """Test TAF initialization with invalid configuration type."""
        with pytest.raises(
            ValueError, match="Config must be TAFConfig instance or dictionary"
        ):
            TAF("invalid_config")

    def test_process_message_valid(self):
        """Test processing a valid message event."""
        taf = TAF({})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello, I need help",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result == "Hello, I need help"

    def test_process_message_empty_body(self):
        """Test processing a message with empty body."""
        taf = TAF({})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result is None

    def test_process_message_whitespace_body(self):
        """Test processing a message with whitespace-only body."""
        taf = TAF({})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "   \n\t   ",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result is None

    def test_process_message_none_body(self):
        """Test processing a message with None body."""
        taf = TAF({})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": None,
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result is None

    def test_process_message_unsupported_event_type(self):
        """Test processing an unsupported event type returns None."""
        taf = TAF({})

        # Test onMessageAdd (real Twilio event, but not supported)
        event_data = {
            "EventType": "onMessageAdd",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello world",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)
        assert result is None

    def test_process_message_participant_event(self):
        """Test processing a participant event returns None."""
        taf = TAF({})

        event_data = {
            "EventType": "onParticipantAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "ParticipantSid": "MBxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        }

        result = taf.process_message(event_data)
        assert result is None

    def test_process_message_invalid_event_data(self):
        """Test processing invalid event data."""
        taf = TAF({})

        # Missing required fields
        invalid_event_data = {"EventType": "onMessageAdded"}

        with pytest.raises(ValueError, match="Invalid webhook event data"):
            taf.process_message(invalid_event_data)

    def test_process_message_real_webhook_data(self):
        """Test processing real webhook data."""
        taf = TAF({})

        real_webhook_data = {
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
            "Body": "Hello oh",
            "ConversationSid": "CHd151e6bcbe3643979a3f41f6d0da3b24",
        }

        result = taf.process_message(real_webhook_data)

        assert result == "Hello oh"

    def test_multiple_message_processing(self):
        """Test that one TAF instance can process multiple messages."""
        taf = TAF({})

        # First message
        event1 = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH111111111111111111111111111111111",
            "Body": "First message",
            "Author": "+11111111111",
        }

        # Second message
        event2 = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CH222222222222222222222222222222222",
            "Body": "Second message",
            "Author": "+22222222222",
        }

        result1 = taf.process_message(event1)
        result2 = taf.process_message(event2)

        # Both should be processed successfully
        assert result1 == "First message"
        assert result2 == "Second message"

    def test_different_config_options(self):
        """Test TAF with different configuration options."""
        default_taf = TAF({})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Test message",
            "Author": "+12345678901",
        }

        result = default_taf.process_message(event_data)

        assert result == "Test message"
