"""Configuration models for the Twilio Agentic Framework."""

from pydantic import BaseModel, ConfigDict, Field


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    memora_base_url: str = Field(
        description="Base URL for Memora API (defaults to production)"
    )

    maestro_base_url: str = Field(
        description="Base URL for Maestro API (defaults to production)"
    )

    twilio_account_sid: str = Field(description="Twilio Account SID")

    conversation_service_sid: str = Field(description="Twilio Conversation Service SID")

    memory_service_sid: str = Field(description="Memora Memory Service SID")

    twilio_auth_token: str = Field(description="Twilio Auth Token from Twilio Console")

    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "memora_base_url": "https://memory.twilio.com/v1",
                "memory_service_sid": "MGxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "maestro_base_url": "https://maestro.twilio.com/v1",
                "conversation_service_sid": "ISxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "twilio_auth_token": "your_auth_token_here",
            }
        },
    )
