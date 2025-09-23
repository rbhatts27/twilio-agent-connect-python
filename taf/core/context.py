from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from ..context.memora import MemoraMemory


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


class SessionContext(BaseModel):
    """
    Session context model for Twilio Agentic Framework.

    This model holds session-specific information including conversation details,
    user profile, and memory for maintaining context.
    """

    profile: Profile = Field(..., description="User profile information")
    memory: Memory = Field(..., description="User memory for conversation context")


class SessionIdentity(BaseModel):
    """
    Identity model for session identification.

    This model holds the unique identifier for a session.
    """

    profile_id: str = Field(..., description="Unique profile identifier")
    conversation_sid: str = Field(..., description="Conversation SID")
