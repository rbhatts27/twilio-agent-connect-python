"""Configuration models for the Twilio Agentic Framework."""

from typing import Optional

from pydantic import BaseModel, Field


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    memora_auth_token: Optional[str] = Field(
        default=None, description="Authentication token for Memora API access"
    )
    memora_base_url: Optional[str] = Field(
        default=None, description="Base URL for Memora API (defaults to production)"
    )

    maestro_base_url: Optional[str] = Field(
        default=None, description="Base URL for Maestro API (defaults to production)"
    )

    twilio_account_sid: Optional[str] = Field(
        default=None, description="Twilio Account SID"
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
