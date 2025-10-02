"""Tests for TAF core class."""

import pytest

from taf import TAF, TAFConfig


def get_test_config():
    """Get a valid test configuration."""
    return {
        "twilio_auth_token": "test_token_123",
        "memora_base_url": "https://memory.twilio.com/v1",
        "memory_service_sid": "MGtest123",
        "maestro_base_url": "https://maestro.twilio.com/v1",
        "twilio_account_sid": "ACtest123",
        "conversation_service_sid": "IS123test",
    }


class TestTAF:
    """Test TAF core class."""

    def test_init_with_config_dict(self):
        """Test TAF initialization with configuration dictionary."""
        config_dict = get_test_config()
        taf = TAF(config_dict)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.twilio_auth_token == "test_token_123"
        assert taf.config.memora_base_url == "https://memory.twilio.com/v1"

    def test_init_with_config_object(self):
        """Test TAF initialization with TAFConfig object."""
        config = TAFConfig(**get_test_config())
        taf = TAF(config)

        assert isinstance(taf.config, TAFConfig)
        assert taf.config.twilio_auth_token == "test_token_123"
        assert taf.config.memora_base_url == "https://memory.twilio.com/v1"

    def test_init_with_empty_config_dict_fails(self):
        """Test TAF initialization with empty configuration dictionary fails."""
        config_dict = {}
        with pytest.raises(ValueError, match="Invalid configuration"):
            TAF(config_dict)

    def test_init_with_invalid_config_type(self):
        """Test TAF initialization with invalid configuration type."""
        with pytest.raises(
            ValueError, match="Config must be TAFConfig instance or dictionary"
        ):
            TAF("invalid_config")
