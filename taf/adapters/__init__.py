"""Adapters for integrating with external services in the Twilio Agentic Framework."""

from typing import List

from .openai_adapter import OpenAIAdapter

__all__: List[str] = ["OpenAIAdapter"]
