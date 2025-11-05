"""
LLM Service for TAF SMS Demo

This module provides an LLM service that processes messages with context from TAF memory.
It builds enhanced system prompts with customer profile information and conversation history.
Uses OpenAI Agents SDK for tool integration and conversation management.
"""

import logging
from typing import Optional

from agents import Agent, Runner
from fastapi import WebSocket
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

# Import tools from tools.py
from tools import confirm_order, create_flex_escalation_tool, look_up_discounts, look_up_order_price

from taf.models.memory import MemoryRetrievalResponse

logger = logging.getLogger(__name__)


class LLMService:
    """Service for processing messages with LLM using TAF memory context and OpenAI Agents SDK."""

    def __init__(self):
        """
        Initialize LLM service with OpenAI Agents SDK.
        """
        # TODO: migrate more tools from demo repo.
        self.tools = [
            look_up_order_price,
            look_up_discounts,
            confirm_order,
        ]

        logger.info(f"LLM service initialized with OpenAI Agents SDK and {len(self.tools)} tools")

    async def process_message(
        self,
        user_message: str,
        memory_response: MemoryRetrievalResponse,
        profile_id: str,
        websocket: Optional[WebSocket],
        conversation_history: list[ChatCompletionMessageParam] | None = None,
    ) -> str:
        """
        Process user message with memory context and generate response using Agents SDK.

        Args:
            user_message: The user's message
            memory_response: Memory response from TAF with observations, summaries, and sessions
            profile_id: User's profile ID
            conversation_history: Optional conversation history (OpenAI ChatCompletionMessageParam format).
                                 If provided, uses this instead of building from TAF session memories.

        Returns:
            Generated response from LLM
        """
        try:
            # Build TAF-enhanced instructions with profile context
            enhanced_instructions = self._build_enhanced_instructions(memory_response, profile_id)

            if websocket is not None:
                tools = self.tools + [create_flex_escalation_tool(websocket)]
            else:
                tools = self.tools

            # Create agent with TAF-enhanced instructions
            agent = Agent(
                name="Owl Internet Customer Service",
                instructions=enhanced_instructions,
                model="gpt-4o",
                tools=tools,
            )

            # Use passed conversation history if provided, otherwise build from TAF session memories
            if conversation_history is not None:
                messages_history = conversation_history
            else:
                messages_history = self._build_conversation_history(memory_response)

            # Format conversation history for agent context
            # Exclude the current user message to avoid duplication (it's at the end of the history)
            previous_messages = messages_history[:-1] if messages_history else []

            if previous_messages:
                # Format previous messages as context
                history_lines = [f"{msg['role']}: {msg['content']}" for msg in previous_messages]
                history_context = "\n".join(history_lines)
                agent_input = f"[Previous conversation]\n{history_context}\n\n[Current message]\n{user_message}"
            else:
                # No previous history, just use the current message
                agent_input = user_message

            # Run the agent with the message (tools are executed automatically)
            result = await Runner.run(agent, input=agent_input)

            # Extract response
            response = str(result.final_output)

            logger.info(f"Generated response for profile {profile_id}: {response[:100]}...")
            return response

        except Exception as e:
            logger.error(f"Error processing message with LLM: {e}", exc_info=True)
            return (
                "I'm sorry, I'm having trouble processing your message right now. Please try again."
            )

    def _build_enhanced_instructions(
        self, memory_response: MemoryRetrievalResponse, profile_id: str
    ) -> str:
        """
        Build enhanced agent instructions with TAF memory context.

        Args:
            memory_response: Memory response from TAF
            profile_id: User's profile ID

        Returns:
            Enhanced instructions string for the agent
        """
        # Build instructions parts
        instruction_parts = [
            "You are Owl Internet's comprehensive customer service assistant.",
            "Your goal is to provide personalized, helpful support using the customer's "
            "interaction history and context.",
            "",
            "=== CUSTOMER PROFILE ===",
            f"- Profile ID: {profile_id}",
            "",
        ]

        # Add relevant context from observations
        if memory_response.observations:
            instruction_parts.append("=== RELEVANT OBSERVATIONS (from TAF Memory) ===")
            for obs in memory_response.observations:
                instruction_parts.append(f"- {obs.content}")
            instruction_parts.append("")

        # Add conversation summaries
        if memory_response.summaries:
            instruction_parts.append("=== CONVERSATION SUMMARIES ===")
            for summary in memory_response.summaries:
                instruction_parts.append(f"- {summary.content}")
            instruction_parts.append("")

        # Add TAF-enhanced behavioral instructions
        instruction_parts.extend(
            [
                "=== BEHAVIOR GUIDELINES ===",
                "1. CONTEXT AWARENESS:",
                "   - Use the conversation history to maintain continuity",
                "   - Reference previous observations to show you remember past interactions",
                "   - Use summaries to understand the broader context",
                "",
                "2. COMMUNICATION STYLE:",
                "   - Keep responses clear, concise, and professional",
                "   - Show empathy and understanding of their situation",
                "   - Be helpful and proactive",
                "",
                "3. SERVICE EXCELLENCE:",
                "   - Provide helpful suggestions when appropriate",
                "   - If you need more information to help, ask specific clarifying questions",
                "   - Use the tools available to you to assist the customer",
                "",
            ]
        )

        return "\n".join(instruction_parts)

    def _build_conversation_history(
        self, memory_response: MemoryRetrievalResponse
    ) -> list[ChatCompletionMessageParam]:
        """
        Build conversation history from session memories.

        Session memories contain previous conversation exchanges with structured messages.

        Args:
            memory_response: Memory response from TAF

        Returns:
            List of OpenAI ChatCompletionMessageParam (properly typed message objects)
        """
        messages: list[ChatCompletionMessageParam] = []

        # Extract messages from session memories
        for session in memory_response.sessions:
            # Each session contains a list of structured messages
            for msg in session.messages:
                # Map direction to role (inbound=user, outbound=assistant)
                if msg.direction == "inbound":
                    user_msg: ChatCompletionUserMessageParam = {
                        "role": "user",
                        "content": msg.content,
                    }
                    messages.append(user_msg)
                else:
                    assistant_msg: ChatCompletionAssistantMessageParam = {
                        "role": "assistant",
                        "content": msg.content,
                    }
                    messages.append(assistant_msg)

        return messages
