"""
LLM Service for TAF SMS Demo

This module provides an LLM service that processes messages with context from TAF memory.
It builds enhanced system prompts with customer profile information and conversation history.
Uses OpenAI Agents SDK for tool integration and conversation management.
"""

import logging

from agents import Agent, Runner

# Import tools from tools.py
from tools import confirm_order, look_up_discounts, look_up_order_price

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
    ) -> str:
        """
        Process user message with memory context and generate response using Agents SDK.

        Args:
            user_message: The user's message
            memory_response: Memory response from TAF with observations, summaries, and sessions
            profile_id: User's profile ID

        Returns:
            Generated response from LLM
        """
        try:
            # Build TAF-enhanced instructions with profile context
            enhanced_instructions = self._build_enhanced_instructions(memory_response, profile_id)

            # Create agent with TAF-enhanced instructions
            agent = Agent(
                name="Owl Internet Customer Service",
                instructions=enhanced_instructions,
                model="gpt-4o",
                tools=self.tools,
            )

            # Build conversation history from TAF session memories
            messages_history = self._build_conversation_history(memory_response)

            # Prepend conversation history to current message if available
            if messages_history:
                # Format history for context
                history_context = "\n".join(
                    [
                        f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                        for msg in messages_history
                    ]
                )
                enhanced_message = f"[Previous conversation]\n{history_context}\n\n[Current message]\n{user_message}"
            else:
                enhanced_message = user_message

            # Run the agent with the message (without session for stateless operation)
            result = await Runner.run(agent, input=enhanced_message)

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

    def _build_conversation_history(self, memory_response: MemoryRetrievalResponse) -> list[dict]:
        """
        Build conversation history from session memories.

        Session memories contain previous conversation exchanges with structured messages.

        Args:
            memory_response: Memory response from TAF

        Returns:
            List of message dicts with role and content
        """
        messages = []

        # Extract messages from session memories
        for session in memory_response.sessions:
            # Each session contains a list of structured messages
            for msg in session.messages:
                # Map direction to role (inbound=user, outbound=assistant)
                role = "user" if msg.direction == "inbound" else "assistant"
                messages.append({"role": role, "content": msg.content})

        return messages
