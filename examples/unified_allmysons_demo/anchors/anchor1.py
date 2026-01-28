"""
Anchor 1: Concurrent Cross-Channel Communication

The Ramirez Family Quote Request - Maria calls for a moving quote (voice),
then texts photos while on the call (SMS). AI handles both channels concurrently.
"""

from typing import Optional

from anchors.base import BaseAnchor
from dashboard.event_handler import push_voice_transcript
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionUserMessageParam,
)

from tac import TAC
from tac.channels import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = get_logger(__name__)


class Anchor1ConcurrentChannels(BaseAnchor):
    """Anchor 1: Concurrent Cross-Channel Communication."""

    anchor_id = "anchor1"
    name = "Concurrent Cross-Channel"
    short_description = "Voice + SMS running simultaneously in one conversation"
    scenario_title = "The Ramirez Family Quote Request"
    scenario_steps = [
        {"number": "1", "text": "Maria calls for a moving quote (Voice)"},
        {"number": "2", "text": "AI asks for furniture photos"},
        {"number": "3", "text": "Maria texts photos while on call (SMS)"},
        {"number": "4", "text": "AI analyzes photos, responds on both channels"},
        {"number": "5", "text": "AI sends detailed quote via SMS"},
    ]

    def __init__(
        self,
        tac: TAC,
        sms_channel: SMSChannel,
        voice_channel: VoiceChannel,
    ) -> None:
        super().__init__(tac, sms_channel, voice_channel)
        self.llm_service = LLMService(tac)

    async def handle_message(
        self,
        user_message: str,
        context: ConversationSession,
        memory_response: Optional[MemoryRetrievalResponse],
        incoming_channel: Optional[str] = None,
    ) -> None:
        """Handle messages with concurrent channel awareness."""
        conv_id = context.conversation_id
        channel = incoming_channel or context.channel

        try:
            # Initialize conversation history if needed
            if conv_id not in self.conversation_messages:
                self.conversation_messages[conv_id] = []

            # Add current user message with channel annotation
            user_msg: ChatCompletionUserMessageParam = {
                "role": "user",
                "content": f"[{channel.upper()}] {user_message}",
            }
            self.conversation_messages[conv_id].append(user_msg)

            # Log incoming message
            logger.info(
                f"\n{'=' * 80}\n"
                f"{'VOICE' if channel == 'voice' else 'SMS'} MESSAGE | "
                f"{user_message[:50]}{'...' if len(user_message) > 50 else ''}",
                conversation_id=conv_id,
                channel=channel,
                profile_id=context.profile_id,
            )

            # Push transcript for real-time display (voice only)
            if channel == "voice":
                push_voice_transcript(
                    conversation_id=conv_id,
                    speaker="customer",
                    text=user_message,
                    profile_id=context.profile_id,
                )

            # Memory retrieval strategy:
            # - Voice: Retrieve once at call start, cache and reuse for entire call
            # - SMS: Use the provided memory_response (retrieved per message)
            is_first_voice_message = False
            if channel == "voice":
                if conv_id not in self.voice_memory_cache:
                    # First voice message - retrieve and cache memory
                    is_first_voice_message = True
                    logger.info(
                        "MEMORY | Retrieving memory for voice call (will be cached)",
                        conversation_id=conv_id,
                    )
                    memory_response = await self.tac.retrieve_memory(context, user_message)
                    if memory_response:
                        self.voice_memory_cache[conv_id] = memory_response
                else:
                    # Subsequent voice messages - use cached memory (no API call)
                    memory_response = self.voice_memory_cache[conv_id]

            # Log memory info
            if memory_response:
                memory_items = []
                if memory_response.observations:
                    memory_items.append(f"{len(memory_response.observations)} observations")
                if memory_response.summaries:
                    memory_items.append(f"{len(memory_response.summaries)} summaries")
                memory_summary = ", ".join(memory_items) if memory_items else "context"

                if channel == "voice" and not is_first_voice_message:
                    # Cached memory for voice - don't log as "Retrieved" to avoid confusion
                    pass
                else:
                    logger.info(
                        f"MEMORY | Retrieved {memory_summary}",
                        conversation_id=conv_id,
                        channel=channel,
                    )

            # Check for concurrent channel activity
            is_concurrent = (
                channel == "sms"
                and conv_id in self.active_voice_calls
                and self.active_voice_calls[conv_id]
            )

            if is_concurrent:
                logger.info(
                    "CONCURRENT | SMS received during active voice call - cross-channel mode",
                    conversation_id=conv_id,
                )

            # Get websocket for voice responses
            active_websocket = (
                self.voice_channel.get_websocket(conv_id) if context.channel == "voice" else None
            )

            # Process message with LLM
            logger.info(
                "AI AGENT | Processing message...",
                conversation_id=conv_id,
                channel=channel,
            )

            llm_response = await self.llm_service.process_message(
                user_message=user_message,
                memory_response=memory_response,
                context=context,
                websocket=active_websocket,
                conversation_history=self.conversation_messages[conv_id],
                incoming_channel=channel,
            )

            # Send response through appropriate channel
            if llm_response:
                if channel == "voice":
                    await self.voice_channel.send_response(conv_id, llm_response, role="assistant")
                elif channel == "sms":
                    await self.sms_channel.send_response(conv_id, llm_response, role="assistant")

                # Log response preview
                response_preview = (
                    llm_response[:100] + "..." if len(llm_response) > 100 else llm_response
                )
                logger.info(
                    f"AI RESPONSE [{channel.upper()}] | {response_preview}",
                    conversation_id=conv_id,
                    channel=channel,
                )

                # Push agent transcript for real-time display (voice only)
                if channel == "voice":
                    push_voice_transcript(
                        conversation_id=conv_id,
                        speaker="agent",
                        text=llm_response,
                        profile_id=context.profile_id,
                    )

                # Store assistant response
                assistant_msg: ChatCompletionAssistantMessageParam = {
                    "role": "assistant",
                    "content": f"[{channel.upper()}] {llm_response}",
                }
                self.conversation_messages[conv_id].append(assistant_msg)

        except Exception as e:
            logger.error(
                "Error processing message",
                conversation_id=conv_id,
                channel=channel,
                error=str(e),
                exc_info=True,
            )
