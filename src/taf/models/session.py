from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from taf.models.memory import ProfileResponse


class ConversationSession(BaseModel):
    """
    Context information for a conversation session that's passed to callbacks.

    This provides the necessary context for developers to handle memory-ready
    events and send responses back through the appropriate channel.
    """

    conversation_id: str = Field(..., description="Unique conversation identifier")
    profile_id: Optional[str] = Field(
        None, description="Profile ID associated with conversation (optional)"
    )
    channel: str = Field(..., description="Channel type (e.g., 'sms', 'voice')")
    started_at: datetime = Field(
        default_factory=datetime.now,
        description="When the conversation session was started",
    )
    profile: Optional[ProfileResponse] = Field(
        None, description="Profile information with traits (optional)"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)
