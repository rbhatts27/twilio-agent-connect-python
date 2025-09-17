import pytest

from taf import (
    TAF,
    ModelProvider,
    TAFConfig,
    TwilioWebhookEvent,
    WebhookEventType,
    __version__,
)


def test_version():
    """Test that version is available and is a string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.1.0"


def test_imports():
    """Test that all main classes can be imported."""
    assert TAF is not None
    assert TAFConfig is not None
    assert ModelProvider is not None
    assert TwilioWebhookEvent is not None
    assert WebhookEventType is not None


def test_basic_taf_functionality():
    """Test basic TAF functionality works."""
    taf = TAF({"model_provider": "openai"})
    assert taf.get_model_provider() == "openai"
