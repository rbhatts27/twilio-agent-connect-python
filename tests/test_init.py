from tac import TAC, TACConfig, TwilioWebhookEvent, WebhookEventType, __version__


def test_version():
    """Test that version is available and is a string."""
    assert isinstance(__version__, str)
    assert __version__ == "0.1.1"


def test_imports():
    """Test that all main classes can be imported."""
    assert TAC is not None
    assert TACConfig is not None
    assert TwilioWebhookEvent is not None
    assert WebhookEventType is not None


def test_basic_tac_functionality():
    """Test basic TAC functionality works."""
    config = {
        "twilio_auth_token": "test_token_123",
        "environment": "prod",
        "twilio_account_sid": "ACtest123",
        "conversation_service_sid": "IS123test",
        "twilio_phone_number": "+15551234567",
    }
    tac = TAC(config)
    assert tac.config.twilio_auth_token == "test_token_123"
