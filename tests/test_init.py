import pytest

from taf import TAF, TAFConfig, TwilioWebhookEvent, WebhookEventType, __version__


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
    taf = TAF({})
    assert taf.config.memora_auth_token is None
