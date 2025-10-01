import pytest

from src.taf import TAF, TAFConfig, TwilioWebhookEvent, WebhookEventType, __version__


def test_version():
    """Test that version is available and is a string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.1.1"


def test_imports():
    """Test that all main classes can be imported."""
    assert TAF is not None
    assert TAFConfig is not None
    assert TwilioWebhookEvent is not None
    assert WebhookEventType is not None


def test_basic_taf_functionality():
    """Test basic TAF functionality works."""
    config = {
        "memora_auth_token": "test_token_123",
        "memora_base_url": "https://memory.twilio.com/v1",
        "maestro_base_url": "https://maestro.twilio.com/v1",
        "twilio_account_sid": "ACtest123",
    }
    taf = TAF(config)
    assert taf.config.memora_auth_token == "test_token_123"
