"""Configuration models for the Twilio Agentic Framework."""

from typing import Optional

from pydantic import BaseModel, Field


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    memora_auth_token: str = Field(
        description="Authentication token for Memora API access"
    )
    memora_base_url: str = Field(
        description="Base URL for Memora API (defaults to production)"
    )

    maestro_base_url: str = Field(
        description="Base URL for Maestro API (defaults to production)"
    )

    twilio_account_sid: str = Field(description="Twilio Account SID")

    log_level: Optional[str] = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "memora_auth_token": "your_auth_token_here",
                "memora_base_url": "https://memory.twilio.com/v1",
                "maestro_base_url": "https://maestro.twilio.com/v1",
            }
        }
