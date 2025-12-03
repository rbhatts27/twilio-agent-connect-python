"""Configuration models for the Twilio Agentic Framework."""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class TwilioMemoryConfig(BaseModel):
    """
    Configuration for Twilio Memory (Memora) integration.

    This config should only be provided if you have purchased Twilio Memory functionality.
    When provided, TAF will automatically retrieve memory for SMS conversations.
    """

    memory_store_id: str = Field(
        description="Memora Memory Store ID (starts with MG)",
    )
    api_key: str = Field(
        description="API Key for Memora authentication",
    )
    api_token: str = Field(
        description="API Token for Memora authentication",
    )

    trait_groups: Optional[list[str]] = Field(
        default=None,
        description="Optional list of trait group names to include when retrieving profiles",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memory_store_id": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "trait_groups": ["Contact", "Preferences"],
                "api_key": "your_api_key_here",
                "api_token": "your_api_token_here",
            }
        },
    )

    @classmethod
    def from_env(cls) -> Optional["TwilioMemoryConfig"]:
        """
        Create TwilioMemoryConfig from environment variables.

        Loads configuration from the following environment variables:
        - TWILIO_TAF_MEMORY_STORE_ID: Memora Memory Store ID (starts with MG)
        - TWILIO_TAF_MEMORY_API_KEY: API Key for Memora authentication
        - TWILIO_TAF_MEMORY_API_TOKEN: API Token for Memora authentication
        - TWILIO_TAF_TRAIT_GROUPS: Comma-separated list of trait groups (optional)

        Returns:
            TwilioMemoryConfig instance if all required env vars are set, None otherwise.

        Example:
            >>> # From environment variables
            >>> config = TwilioMemoryConfig.from_env()

            >>> # Or manually construct with custom trait_groups
            >>> config = TwilioMemoryConfig(
            >>>     memory_store_id="MG123",
            >>>     api_key="key",
            >>>     api_token="token",
            >>>     trait_groups=["Contact", "Preferences"],
            >>> )
        """
        memory_store_id = os.environ.get("TWILIO_TAF_MEMORY_STORE_ID")
        api_key = os.environ.get("TWILIO_TAF_MEMORY_API_KEY")
        api_token = os.environ.get("TWILIO_TAF_MEMORY_API_TOKEN")

        # Return None if any required variable is missing
        if not (memory_store_id and api_key and api_token):
            return None

        # Parse trait groups from environment variable
        trait_groups = None
        trait_groups_str = os.environ.get("TWILIO_TAF_TRAIT_GROUPS")
        if trait_groups_str:
            trait_groups = [g.strip() for g in trait_groups_str.split(",")]

        return cls(
            memory_store_id=memory_store_id,
            api_key=api_key,
            api_token=api_token,
            trait_groups=trait_groups,
        )


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    environment: str = Field(description="TAF environment (dev, stage, or prod)")
    conversation_service_sid: str = Field(description="Twilio Conversation Service SID")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate that environment is one of the allowed values."""
        allowed = {"dev", "stage", "prod"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    twilio_memory_config: Optional[TwilioMemoryConfig] = Field(
        default=None,
        description="Optional Twilio Memory configuration. Provide this if you have "
        "purchased Twilio Memory functionality. When provided, memory will be "
        "automatically retrieved for SMS conversations.",
    )

    twilio_account_sid: str = Field(description="Twilio Account SID")
    twilio_auth_token: str = Field(description="Twilio Auth Token from Twilio Console")

    twilio_phone_number: str = Field(description="Twilio Phone Number to use for sending messages")

    knowledge_base_id: Optional[str] = Field(
        default=None,
        description="Optional Knowledge Base ID for knowledge search functionality",
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memora_base_url(self) -> str:
        """Return the Memora base URL based on the environment."""
        memora_urls = {
            "dev": "https://memory.dev.twilio.com",
            "stage": "https://memory.stage.twilio.com",
            "prod": "https://memory.twilio.com",
        }
        return memora_urls[self.environment]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def maestro_base_url(self) -> str:
        """Return the Maestro base URL based on the environment."""
        maestro_urls = {
            "dev": "https://conversations.dev.twilio.com",
            "stage": "https://conversations.stage.twilio.com",
            "prod": "https://conversations.twilio.com",
        }
        return maestro_urls[self.environment]

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "environment": "prod",
                "conversation_service_sid": "ISxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_auth_token": "your_auth_token_here",
                "twilio_phone_number": "your_phone_number_here",
                "twilio_memory_config": {
                    "memory_store_id": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                    "api_key": "your_api_key_here",
                    "api_token": "your_api_token_here",
                    "trait_groups": ["Contact", "Preferences"],
                },
            }
        },
    )

    @classmethod
    def from_env(cls) -> "TAFConfig":
        """
        Create TAFConfig from environment variables.

        Loads configuration from the following environment variables:
        - TWILIO_TAF_ENVIRONMENT: TAF environment (dev, stage, or prod)
        - TWILIO_TAF_CONVERSATION_SERVICE_SID: Twilio Conversation Service SID
        - TWILIO_TAF_ACCOUNT_SID: Twilio Account SID
        - TWILIO_TAF_AUTH_TOKEN: Twilio Auth Token
        - TWILIO_TAF_PHONE_NUMBER: Twilio Phone Number
        - TWILIO_TAF_KNOWLEDGE_BASE_ID: Knowledge Base ID (optional)
        - TWILIO_TAF_LOG_LEVEL: Logging level (optional, defaults to INFO)

        Memory configuration is automatically loaded via TwilioMemoryConfig.from_env()
        from these environment variables (all optional):
        - TWILIO_TAF_MEMORY_STORE_ID: Memora Memory Store ID
        - TWILIO_TAF_MEMORY_API_KEY: API Key for Memora
        - TWILIO_TAF_MEMORY_API_TOKEN: API Token for Memora
        - TWILIO_TAF_TRAIT_GROUPS: Comma-separated list of trait groups

        Returns:
            TAFConfig instance with all configuration loaded from environment.

        Raises:
            KeyError: If required environment variables are not set.
            ValidationError: If environment variable values are invalid.

        Example:
            >>> # With all env vars set in .env file
            >>> config = TAFConfig.from_env()
            >>> taf = TAF(config=config)

            >>> # Or fall back to manual config if env vars not set
            >>> try:
            >>>     config = TAFConfig.from_env()
            >>> except (KeyError, ValidationError):
            >>>     config = TAFConfig(environment="prod", ...)
        """
        # Load optional memory configuration
        twilio_memory_config = TwilioMemoryConfig.from_env()

        return cls(
            environment=os.environ["TWILIO_TAF_ENVIRONMENT"],
            conversation_service_sid=os.environ["TWILIO_TAF_CONVERSATION_SERVICE_SID"],
            twilio_account_sid=os.environ["TWILIO_TAF_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_TAF_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_TAF_PHONE_NUMBER"],
            knowledge_base_id=os.environ.get("TWILIO_TAF_KNOWLEDGE_BASE_ID"),
            log_level=os.environ.get("TWILIO_TAF_LOG_LEVEL", "INFO"),
            twilio_memory_config=twilio_memory_config,
        )
