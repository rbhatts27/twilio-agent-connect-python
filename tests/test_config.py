"""Tests for TAF configuration models."""

import pytest
from pydantic import ValidationError

from taf import TAFConfig


class TestTAFConfig:
    """Test TAFConfig model."""

    def test_config_with_required_fields(self):
        """Test config with all required fields."""
        config = TAFConfig(
            twilio_auth_token="test_token_123",
            memora_base_url="https://memory.twilio.com/v1",
            maestro_base_url="https://maestro.twilio.com/v1",
            twilio_account_sid="ACtest123",
        )
        assert config.twilio_auth_token == "test_token_123"
        assert config.memora_base_url == "https://memory.twilio.com/v1"
        assert config.maestro_base_url == "https://maestro.twilio.com/v1"
        assert config.twilio_account_sid == "ACtest123"
        assert config.log_level == "INFO"  # Default value

    def test_config_with_custom_log_level(self):
        """Test config with custom log level."""
        config = TAFConfig(
            twilio_auth_token="test_token_123",
            memora_base_url="https://memory.twilio.com/v1",
            maestro_base_url="https://maestro.twilio.com/v1",
            twilio_account_sid="ACtest123",
            log_level="DEBUG",
        )
        assert config.twilio_auth_token == "test_token_123"
        assert config.memora_base_url == "https://memory.twilio.com/v1"
        assert config.maestro_base_url == "https://maestro.twilio.com/v1"
        assert config.twilio_account_sid == "ACtest123"
        assert config.log_level == "DEBUG"

    def test_config_dict_conversion(self):
        """Test converting config to dictionary."""
        config = TAFConfig(
            twilio_auth_token="test_token_123",
            memora_base_url="https://memory.twilio.com/v1",
            maestro_base_url="https://maestro.twilio.com/v1",
            twilio_account_sid="ACtest123",
        )
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert "twilio_auth_token" in config_dict
        assert config_dict["twilio_auth_token"] == "test_token_123"
        assert "log_level" in config_dict
        assert config_dict["log_level"] == "INFO"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_data = {
            "twilio_auth_token": "test_token_123",
            "memora_base_url": "https://memory.twilio.com/v1",
            "maestro_base_url": "https://maestro.twilio.com/v1",
            "twilio_account_sid": "ACtest123",
        }
        config = TAFConfig(**config_data)
        assert config.twilio_auth_token == "test_token_123"
        assert config.memora_base_url == "https://memory.twilio.com/v1"

    def test_config_json_schema(self):
        """Test that config has valid JSON schema."""
        schema = TAFConfig.model_json_schema()

        assert "properties" in schema
        assert "twilio_auth_token" in schema["properties"]
        assert "memora_base_url" in schema["properties"]
        assert "maestro_base_url" in schema["properties"]
        assert "twilio_account_sid" in schema["properties"]
        assert "log_level" in schema["properties"]

        # Check required fields
        assert "required" in schema
        required_fields = schema["required"]
        assert "twilio_auth_token" in required_fields
        assert "memora_base_url" in required_fields
        assert "maestro_base_url" in required_fields
        assert "twilio_account_sid" in required_fields

    def test_config_equality(self):
        """Test config equality comparison."""
        base_config = {
            "twilio_auth_token": "test_token_123",
            "memora_base_url": "https://memory.twilio.com/v1",
            "maestro_base_url": "https://maestro.twilio.com/v1",
            "twilio_account_sid": "ACtest123",
        }
        config1 = TAFConfig(**base_config)
        config2 = TAFConfig(**base_config)

        different_config = base_config.copy()
        different_config["twilio_auth_token"] = "different_token"
        config3 = TAFConfig(**different_config)

        assert config1 == config2
        assert config1 != config3

    def test_missing_required_fields(self):
        """Test that missing required fields raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TAFConfig()

        error = exc_info.value
        assert "twilio_auth_token" in str(error)
        assert "memora_base_url" in str(error)
        assert "maestro_base_url" in str(error)
        assert "twilio_account_sid" in str(error)

    def test_partial_config_fails(self):
        """Test that partial config raises validation error."""
        with pytest.raises(ValidationError):
            TAFConfig(
                twilio_auth_token="test_token_123"
            )  # Missing other required fields
