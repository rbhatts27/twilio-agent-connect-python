"""Tests for TAF core class."""

import pytest
from pydantic import ValidationError

from taf import TAF, ModelProvider, TAFConfig


class TestTAF:
    """Test TAF core class."""

    def test_init_with_config_dict(self):
        """Test TAF initialization with configuration dictionary."""
        config_dict = {"model_provider": "openai"}
        taf = TAF(config_dict)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.model_provider == ModelProvider.OPENAI

    def test_init_with_config_object(self):
        """Test TAF initialization with TAFConfig object."""
        config = TAFConfig(model_provider=ModelProvider.OPENAI)
        taf = TAF(config)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.model_provider == ModelProvider.OPENAI

    def test_init_with_invalid_config_dict(self):
        """Test TAF initialization with invalid configuration dictionary."""
        invalid_config = {"model_provider": "invalid_provider"}

        with pytest.raises(ValueError, match="Invalid configuration"):
            TAF(invalid_config)

    def test_init_with_invalid_config_type(self):
        """Test TAF initialization with invalid configuration type."""
        with pytest.raises(
            ValueError, match="Config must be TAFConfig instance or dictionary"
        ):
            TAF("invalid_config")

    def test_process_message_valid(self):
        """Test processing a valid message event."""
        taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello, I need help",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert isinstance(result, dict)
        assert "event" in result
        assert "processing" in result
        assert "config" in result

        # Check event data
        assert result["event"]["type"] == "onMessageAdded"
        assert result["event"]["conversation_sid"] == "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert result["event"]["body"] == "Hello, I need help"
        assert result["event"]["author"] == "+12345678901"
        assert result["event"]["is_message_event"] is True

        # Check processing decision
        assert result["processing"]["should_process"] is True
        assert result["processing"]["model_provider"] == "openai"

        # Check config
        assert result["config"]["model_provider"] == "openai"

    def test_process_message_empty_body(self):
        """Test processing a message with empty body."""
        taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result["processing"]["should_process"] is False

    def test_process_message_whitespace_body(self):
        """Test processing a message with whitespace-only body."""
        taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "   \n\t   ",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result["processing"]["should_process"] is False

    def test_process_message_none_body(self):
        """Test processing a message with None body."""
        taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": None,
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result["processing"]["should_process"] is False

    def test_process_message_non_message_event(self):
        """Test processing a non-message event."""
        taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "someOtherEvent",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello world",
            "Author": "+12345678901",
        }

        result = taf.process_message(event_data)

        assert result["event"]["is_message_event"] is False
        assert result["processing"]["should_process"] is False

    def test_process_message_invalid_event_data(self):
        """Test processing invalid event data."""
        taf = TAF({"model_provider": "openai"})

        # Missing required fields
        invalid_event_data = {"EventType": "onMessageAdded"}

        with pytest.raises(ValueError, match="Invalid webhook event data"):
            taf.process_message(invalid_event_data)

    def test_process_message_real_webhook_data(self):
        """Test processing real webhook data."""
        taf = TAF({"model_provider": "openai"})

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

        assert result["event"]["type"] == "onMessageAdded"
        assert (
            result["event"]["conversation_sid"] == "CHd151e6bcbe3643979a3f41f6d0da3b24"
        )
        assert result["event"]["body"] == "Hello oh"
        assert result["event"]["author"] == "+12162622233"
        assert result["processing"]["should_process"] is True

    def test_get_model_provider(self):
        """Test get_model_provider method."""
        taf = TAF({"model_provider": "openai"})

        assert taf.get_model_provider() == "openai"

    def test_repr(self):
        """Test string representation of TAF instance."""
        taf = TAF({"model_provider": "openai"})

        repr_str = repr(taf)
        assert "TAF" in repr_str
        assert "model_provider=openai" in repr_str

    def test_multiple_message_processing(self):
        """Test that one TAF instance can process multiple messages."""
        taf = TAF({"model_provider": "openai"})

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
        assert result1["processing"]["should_process"] is True
        assert result2["processing"]["should_process"] is True

        # Different conversation IDs
        assert (
            result1["event"]["conversation_sid"] != result2["event"]["conversation_sid"]
        )

        # Same model provider for both
        assert (
            result1["processing"]["model_provider"]
            == result2["processing"]["model_provider"]
            == "openai"
        )

    def test_different_model_providers(self):
        """Test TAF with different model providers."""
        openai_taf = TAF({"model_provider": "openai"})

        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Test message",
            "Author": "+12345678901",
        }

        openai_result = openai_taf.process_message(event_data)

        assert openai_result["processing"]["model_provider"] == "openai"
