"""Pydantic models for Twilio ConversationRelay Voice WebSocket messages."""

from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


class CustomParameters(BaseModel):
    """Custom parameters passed in ConversationRelay setup."""

    conversation_id: Optional[str] = Field(None, alias="conversationId")
    profile_id: Optional[str] = Field(None, alias="profileId")

    model_config = {"populate_by_name": True}


class SetupMessage(BaseModel):
    """
    Setup message sent when WebSocket connection is established.

    Contains call metadata and custom parameters from TwiML.
    """

    type: Literal["setup"] = "setup"
    session_id: Optional[str] = Field(None, alias="sessionId")
    call_sid: Optional[str] = Field(None, alias="callSid")
    parent_call_sid: Optional[str] = Field(None, alias="parentCallSid")
    from_number: Optional[str] = Field(None, alias="from")
    to_number: Optional[str] = Field(None, alias="to")
    forwarded_from: Optional[str] = Field(None, alias="forwardedFrom")
    caller_name: Optional[str] = Field(None, alias="callerName")
    direction: Optional[str] = Field(None, description="Call direction (inbound/outbound)")
    call_type: Optional[str] = Field(None, alias="callType", description="Call type (e.g., PSTN)")
    call_status: Optional[str] = Field(None, alias="callStatus", description="Call status")
    account_sid: Optional[str] = Field(None, alias="accountSid")
    custom_parameters: Optional[CustomParameters] = Field(None, alias="customParameters")

    model_config = {"populate_by_name": True}


class PromptMessage(BaseModel):
    """
    Prompt message containing user's voice input.

    Sent when user speaks and speech is transcribed.
    """

    type: Literal["prompt"] = "prompt"
    conversation_id: Optional[str] = Field(None, alias="conversationId")
    voice_prompt: Optional[str] = Field(
        None, alias="voicePrompt", description="Transcribed user speech"
    )
    lang: Optional[str] = Field(None, description="Language code (e.g., 'en-US')")
    last: Optional[bool] = Field(None, description="Whether this is the last chunk")

    model_config = {"populate_by_name": True}


class InterruptMessage(BaseModel):
    """
    Interrupt message sent when user interrupts the agent.

    Contains information about what was being said when interrupted.
    """

    type: Literal["interrupt"] = "interrupt"
    conversation_id: Optional[str] = Field(None, alias="conversationId")
    utterance_until_interrupt: Optional[str] = Field(
        None,
        alias="utteranceUntilInterrupt",
        description="Text being spoken when interrupted",
    )
    duration_until_interrupt_ms: Optional[int] = Field(
        None,
        alias="durationUntilInterruptMs",
        description="Duration in milliseconds until interruption",
    )

    model_config = {"populate_by_name": True}


# Discriminated union of all voice message types
VoiceMessage = Union[SetupMessage, PromptMessage, InterruptMessage]
