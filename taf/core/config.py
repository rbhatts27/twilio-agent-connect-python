"""Configuration models for the Twilio Agentic Framework."""

from typing import Optional

from pydantic import BaseModel, Field


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    memora_service_id: Optional[str] = Field(
        default=None, description="Memora service ID for memory management"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "memora_service_id": "memora_service_123",
            }
        }
