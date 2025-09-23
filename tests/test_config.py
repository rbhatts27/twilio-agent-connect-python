"""Tests for TAF configuration models."""

import pytest
from pydantic import ValidationError

from taf.core.config import TAFConfig


class TestTAFConfig:
    """Test TAFConfig model."""

    def test_default_config(self):
        """Test config with default values."""
        config = TAFConfig()
        assert config.memora_service_id is None

    def test_config_with_memora_service_id(self):
        """Test config with Memora service ID."""
        config = TAFConfig(memora_service_id="test_service_123")
        assert config.memora_service_id == "test_service_123"

    def test_config_dict_conversion(self):
        """Test converting config to dictionary."""
        config = TAFConfig(memora_service_id="test_service_123")
        config_dict = config.model_dump()

        assert isinstance(config_dict, dict)
        assert "memora_service_id" in config_dict
        assert config_dict["memora_service_id"] == "test_service_123"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_data = {"memora_service_id": "test_service_123"}
        config = TAFConfig(**config_data)
        assert config.memora_service_id == "test_service_123"

    def test_config_json_schema(self):
        """Test that config has valid JSON schema."""
        schema = TAFConfig.model_json_schema()

        assert "properties" in schema
        assert "memora_service_id" in schema["properties"]
        assert "example" in schema

    def test_config_equality(self):
        """Test config equality comparison."""
        config1 = TAFConfig(memora_service_id="test_service_123")
        config2 = TAFConfig(memora_service_id="test_service_123")
        config3 = TAFConfig()

        assert config1 == config2
        assert config1 != config3

    def test_empty_config(self):
        """Test empty config is valid."""
        config = TAFConfig()
        assert config.memora_service_id is None
