"""Tests for TAF configuration models."""

import pytest
from pydantic import ValidationError

from taf.core.config import TAFConfig


class TestTAFConfig:
    """Test TAFConfig model."""

    def test_default_config(self):
        """Test config with default values."""
        config = TAFConfig()
        assert config.memora_auth_token is None
        assert config.memora_base_url is None
        assert config.maestro_base_url is None
        assert config.twilio_account_sid is None

    def test_config_with_values(self):
        """Test config with actual field values."""
        config = TAFConfig(
            memora_auth_token="test_token_123",
            memora_base_url="https://memory.twilio.com/v1",
            maestro_base_url="https://maestro.twilio.com/v1",
            twilio_account_sid="ACtest123",
        )
        assert config.memora_auth_token == "test_token_123"
        assert config.memora_base_url == "https://memory.twilio.com/v1"
        assert config.maestro_base_url == "https://maestro.twilio.com/v1"
        assert config.twilio_account_sid == "ACtest123"

    def test_config_dict_conversion(self):
        """Test converting config to dictionary."""
        config = TAFConfig(memora_auth_token="test_token_123")
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert "memora_auth_token" in config_dict
        assert config_dict["memora_auth_token"] == "test_token_123"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_data = {"memora_auth_token": "test_token_123"}
        config = TAFConfig(**config_data)
        assert config.memora_auth_token == "test_token_123"

    def test_config_json_schema(self):
        """Test that config has valid JSON schema."""
        schema = TAFConfig.model_json_schema()

        assert "properties" in schema
        assert "memora_auth_token" in schema["properties"]
        assert "memora_base_url" in schema["properties"]
        assert "maestro_base_url" in schema["properties"]
        assert "twilio_account_sid" in schema["properties"]

    def test_config_equality(self):
        """Test config equality comparison."""
        config1 = TAFConfig(memora_auth_token="test_token_123")
        config2 = TAFConfig(memora_auth_token="test_token_123")
        config3 = TAFConfig()

        assert config1 == config2
        assert config1 != config3

    def test_empty_config(self):
        """Test empty config is valid."""
        config = TAFConfig()
        assert config.memora_auth_token is None
        assert config.memora_base_url is None
        assert config.maestro_base_url is None
        assert config.twilio_account_sid is None
