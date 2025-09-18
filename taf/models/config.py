"""Configuration models for the Twilio Agentic Framework."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ModelProvider(str, Enum):
    """Available AI model providers."""

    OPENAI = "openai"


class TAFConfig(BaseModel):
    """Configuration model for Twilio Agentic Framework settings."""

    model_provider: ModelProvider = Field(
        default=ModelProvider.OPENAI, description="AI model provider to use"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {"example": {"model_provider": "openai"}}
