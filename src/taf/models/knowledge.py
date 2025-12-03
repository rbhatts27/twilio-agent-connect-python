"""Knowledge models for the Twilio Agentic Framework."""

from typing import Literal

from pydantic import BaseModel


class Knowledge(BaseModel):
    """Represents a Twilio Knowledge resource."""

    id: str
    name: str
    description: str
    type: Literal["Web", "File", "Text", "DB"]


class KnowledgeBase(BaseModel):
    """Represents a Twilio Knowledge Base resource."""

    id: str
    name: str
    description: str
