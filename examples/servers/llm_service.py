"""
LLM Service for Voice Server with Streaming Support

Provides streaming LLM responses using OpenAI with memory integration.
"""

import asyncio
import logging
import os
from collections.abc import AsyncGenerator

import openai
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

from taf.core.taf import TAF
from taf.models.session import ConversationSession

logger = logging.getLogger(__name__)


class LLMService:
    """Service for streaming LLM responses with memory context."""

    def __init__(self, taf: TAF, system_prompt: str):
        """
        Initialize LLM service.

        Args:
            taf: TAF instance for memory operations
            system_prompt: Base system prompt for the assistant
        """
        self.taf = taf
        self.system_prompt = system_prompt
        self.openai_client = openai.AsyncOpenAI(api_key=os.environ.get("TWILIO_TAF_OPENAI_API_KEY"))
        # Conversation history per conversation_id
        self.conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}

    async def stream_response(
        self,
        prompt: str,
        conv_id: str,
        context: ConversationSession,
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response with memory retrieval and context.

        Args:
            prompt: User's message
            conv_id: Conversation ID
            context: Conversation session context

        Yields:
            Response chunks from the LLM
        """
        try:
            logger.info(f"[LLM] Processing prompt for conversation {conv_id[:8]}...")

            # Initialize conversation history if needed
            if conv_id not in self.conversation_messages:
                system_msg: ChatCompletionSystemMessageParam = {
                    "role": "system",
                    "content": self.system_prompt,
                }
                self.conversation_messages[conv_id] = [system_msg]

            # Add current user message to history
            user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": prompt}
            self.conversation_messages[conv_id].append(user_msg)

            # Retrieve memory if enabled
            memory_response = None
            if self.taf.is_twilio_memory_enabled():
                try:
                    memory_response = await self.taf.retrieve_memory(context, query=prompt)
                    if memory_response:
                        obs_count = (
                            len(memory_response.observations) if memory_response.observations else 0
                        )
                        sum_count = (
                            len(memory_response.summaries) if memory_response.summaries else 0
                        )
                        logger.info(
                            f"[MEMORY] Retrieved {obs_count} observations, {sum_count} summaries"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to retrieve memory for conversation {conv_id}: {e}",
                        exc_info=True,
                    )

            # Build enhanced system prompt with memory context
            enhanced_system_prompt = self.system_prompt
            if memory_response:
                context_parts = [self.system_prompt, "\n=== RELEVANT CONTEXT ==="]
                if memory_response.observations:
                    context_parts.append("\nObservations:")
                    for obs in memory_response.observations[:3]:  # Limit to top 3
                        context_parts.append(f"- {obs.content}")
                enhanced_system_prompt = "\n".join(context_parts)
                self.conversation_messages[conv_id][0] = {
                    "role": "system",
                    "content": enhanced_system_prompt,
                }

            # Stream response from OpenAI
            stream = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=self.conversation_messages[conv_id],
                stream=True,
            )

            full_response = ""
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # Add assistant response to history
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": full_response,
            }
            self.conversation_messages[conv_id].append(assistant_msg)
            logger.info(f"[LLM] Completed streaming {len(full_response)} characters")

        except asyncio.CancelledError:
            logger.info(f"[LLM] Streaming cancelled for conversation {conv_id}")
            raise
        except Exception as e:
            logger.error(f"[LLM] Error in stream_response: {e}", exc_info=True)
            yield "I'm sorry, I'm having trouble processing your message right now."
