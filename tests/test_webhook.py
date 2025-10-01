"""Tests for Twilio webhook event models."""

import pytest
from pydantic import ValidationError

from taf import TwilioWebhookEvent, WebhookEventType


class TestWebhookEventType:
    """Test WebhookEventType enum."""

    def test_message_added_event(self):
        """Test onMessageAdded event type."""
        assert WebhookEventType.ONMESSAGEADDED == "onMessageAdded"

    def test_enum_values(self):
        """Test enum contains expected values."""
        event_types = list(WebhookEventType)
        assert len(event_types) == 1
        assert WebhookEventType.ONMESSAGEADDED in event_types


class TestTwilioWebhookEvent:
    """Test TwilioWebhookEvent model."""

    def test_minimal_valid_event(self):
        """Test creating event with minimal required fields."""
        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        }
        event = TwilioWebhookEvent(**event_data)

        assert event.EventType == "onMessageAdded"
        assert event.ConversationSid == "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert event.Body is None
        assert event.Author is None

    def test_complete_message_event(self):
        """Test creating complete message event."""
        event_data = {
            "EventType": "onMessageAdded",
            "ConversationSid": "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "Body": "Hello world",
            "Author": "+12345678901",
        }
        event = TwilioWebhookEvent(**event_data)

        assert event.EventType == "onMessageAdded"
        assert event.ConversationSid == "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert event.Body == "Hello world"
        assert event.Author == "+12345678901"

    def test_is_message_event(self):
        """Test is_message_event method."""
        # Valid message event
        message_event = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        )
        assert message_event.is_message_event() is True

        # Non-message event
        other_event = TwilioWebhookEvent(
            EventType="someOtherEvent",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        )
        assert other_event.is_message_event() is False

    def test_should_process_with_agent(self):
        """Test should_process_with_agent method."""
        # Valid message that should be processed
        valid_message = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body="Hello, I need help",
            Author="+12345678901",
        )
        assert valid_message.should_process_with_agent() is True

        # Empty message should not be processed
        empty_message = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body="",
            Author="+12345678901",
        )
        assert empty_message.should_process_with_agent() is False

        # Whitespace-only message should not be processed
        whitespace_message = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body="   \n\t   ",
            Author="+12345678901",
        )
        assert whitespace_message.should_process_with_agent() is False

        # None body should not be processed
        none_body = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body=None,
            Author="+12345678901",
        )
        assert none_body.should_process_with_agent() is False

        # Non-message event should not be processed
        non_message = TwilioWebhookEvent(
            EventType="someOtherEvent",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body="Hello world",
            Author="+12345678901",
        )
        assert non_message.should_process_with_agent() is False

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        # Missing EventType
        with pytest.raises(ValidationError):
            TwilioWebhookEvent(ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")

        # Missing ConversationSid
        with pytest.raises(ValidationError):
            TwilioWebhookEvent(EventType="onMessageAdded")

        # Both missing
        with pytest.raises(ValidationError):
            TwilioWebhookEvent()

    def test_real_webhook_data(self):
        """Test with real webhook data structure."""
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

        event = TwilioWebhookEvent(**real_webhook_data)

        assert event.EventType == "onMessageAdded"
        assert event.ConversationSid == "CHd151e6bcbe3643979a3f41f6d0da3b24"
        assert event.Body == "Hello oh"
        assert event.Author == "+12162622233"
        assert event.is_message_event() is True
        assert event.should_process_with_agent() is True

    def test_event_dict_conversion(self):
        """Test converting event to dictionary."""
        event = TwilioWebhookEvent(
            EventType="onMessageAdded",
            ConversationSid="CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            Body="Test message",
            Author="+12345678901",
        )

        event_dict = event.model_dump()

        assert isinstance(event_dict, dict)
        assert event_dict["EventType"] == "onMessageAdded"
        assert event_dict["ConversationSid"] == "CHxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        assert event_dict["Body"] == "Test message"
        assert event_dict["Author"] == "+12345678901"

    def test_event_json_schema(self):
        """Test that event has valid JSON schema."""
        schema = TwilioWebhookEvent.model_json_schema()

        assert "properties" in schema
        assert "EventType" in schema["properties"]
        assert "ConversationSid" in schema["properties"]
        assert "Body" in schema["properties"]
        assert "Author" in schema["properties"]
        assert "example" in schema
