"""Configuration models for the Twilio Agentic Framework."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    environment: Literal["dev", "stage", "prod"] = Field(
        description="TAF environment (dev, stage, or prod)"
    )
    conversation_service_sid: str = Field(description="Twilio Conversation Service SID")
    memory_service_sid: str = Field(description="Memora Memory Service SID")

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
                "memory_service_sid": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "conversation_service_sid": "ISxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_auth_token": "your_auth_token_here",
                "twilio_phone_number": "your_phone_number_here",
            }
        },
    )
