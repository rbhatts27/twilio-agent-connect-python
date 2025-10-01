from typing import TYPE_CHECKING, List, Optional

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
