from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from taf.context.memora import MemoraMemory


class Profile(BaseModel):
    """
    User profile information.
    """

    id: str = Field(..., description="User identifier")


class Memory(BaseModel):
    """
    User memory for maintaining conversation context and session information.
    """

    conversation_sid: str = Field(..., description="Conversation SID")
    memory_list: Optional[List["MemoraMemory"]] = Field(
        default=None, description="A list of memory items"
    )


class SessionIdentity(BaseModel):
    """
    Identity model for session identification.

    This model holds the unique identifier for a session.
    """

    profile_id: str = Field(..., description="Unique profile identifier")
    conversation_id: str = Field(..., description="Conversation SID")


class ConversationContext(BaseModel):
    """
    Context information for a conversation that's passed to callbacks.

    This provides the necessary context for developers to handle memory-ready
    events and send responses back through the appropriate channel.
    """

    conversation_id: str = Field(..., description="Unique conversation identifier")
    profile_id: str = Field(..., description="Profile ID associated with conversation")
    channel: str = Field(..., description="Channel type (e.g., 'sms', 'voice')")
