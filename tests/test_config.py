"""Tests for TAF configuration models."""

import pytest
from pydantic import ValidationError

from taf.models.config import ModelProvider, TAFConfig


class TestModelProvider:
    """Test ModelProvider enum."""

    def test_available_providers(self):
        """Test that all expected providers are available."""
        assert ModelProvider.OPENAI == "openai"

    def test_enum_values(self):
        """Test enum string values."""
        providers = list(ModelProvider)
        assert len(providers) == 1
        assert ModelProvider.OPENAI in providers


class TestTAFConfig:
    """Test TAFConfig model."""

    def test_default_config(self):
        """Test config with default values."""
        config = TAFConfig()
        assert config.model_provider == ModelProvider.OPENAI

    def test_config_with_openai(self):
        """Test config with OpenAI provider."""
        config = TAFConfig(model_provider=ModelProvider.OPENAI)
        assert config.model_provider == ModelProvider.OPENAI

    def test_config_with_string_provider(self):
        """Test config with string provider value."""
        config = TAFConfig(model_provider="openai")
        assert config.model_provider == "openai"

    def test_config_dict_conversion(self):
        """Test converting config to dictionary."""
        config = TAFConfig(model_provider=ModelProvider.OPENAI)
        config_dict = config.dict()

        assert isinstance(config_dict, dict)
        assert "model_provider" in config_dict
        assert config_dict["model_provider"] == "openai"

    def test_invalid_provider(self):
        """Test that invalid provider raises ValidationError."""
        with pytest.raises(ValidationError):
            TAFConfig(model_provider="invalid_provider")

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        config_data = {"model_provider": "openai"}
        config = TAFConfig(**config_data)
        assert config.model_provider == ModelProvider.OPENAI

    def test_config_json_schema(self):
        """Test that config has valid JSON schema."""
        schema = TAFConfig.schema()

        assert "properties" in schema
        assert "model_provider" in schema["properties"]
        assert "example" in schema

    def test_config_equality(self):
        """Test config equality comparison."""
        config1 = TAFConfig(model_provider=ModelProvider.OPENAI)
        config2 = TAFConfig(model_provider=ModelProvider.OPENAI)
        config3 = TAFConfig(model_provider="openai")

        assert config1 == config2
        # String and enum should be equal due to use_enum_values=True
        assert config1.model_provider == config3.model_provider
