"""Configuration models for the Twilio Agentic Framework."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TwilioMemoryConfig(BaseModel):
    """
    Configuration for Twilio Memory (Memora) integration.

    This config should only be provided if you have purchased Twilio Memory functionality.
    When provided, TAF will automatically retrieve memory for SMS conversations.
    """

    memory_store_id: str = Field(
        description="Memora Memory Store ID (starts with MG)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "memory_store_id": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            }
        },
    )


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    environment: Literal["dev", "stage", "prod"] = Field(
        description="TAF environment (dev, stage, or prod)"
    )
    conversation_service_sid: str = Field(description="Twilio Conversation Service SID")

    twilio_memory_config: Optional[TwilioMemoryConfig] = Field(
        default=None,
        description="Optional Twilio Memory configuration. Provide this if you have "
        "purchased Twilio Memory functionality. When provided, memory will be "
        "automatically retrieved for SMS conversations.",
    )

    twilio_account_sid: str = Field(description="Twilio Account SID")
    twilio_auth_token: str = Field(description="Twilio Auth Token from Twilio Console")

    twilio_phone_number: str = Field(description="Twilio Phone Number to use for sending messages")

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def memora_base_url(self) -> str:
        """Return the Memora base URL based on the environment."""
        memora_urls = {
            "dev": "https://memory.dev.twilio.com/v1",
            "stage": "https://memory.stage.twilio.com/v1",
            "prod": "https://memory.twilio.com/v1",
        }
        return memora_urls[self.environment]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def maestro_base_url(self) -> str:
        """Return the Maestro base URL based on the environment."""
        maestro_urls = {
            "dev": "https://conversations.dev.twilio.com/v2",
            "stage": "https://conversations.stage.twilio.com/v2",
            "prod": "https://conversations.twilio.com/v2",
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
                },
            }
        },
    )
