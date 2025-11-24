"""
LLM Service for TAF SMS Demo

This module provides an LLM service that processes messages with context from TAF memory.
It builds enhanced system prompts with customer profile information and conversation history.
Uses OpenAI Agents SDK for tool integration and conversation management.
"""

import logging
from typing import Optional

from agents import Agent, RunConfig, Runner
from fastapi import WebSocket
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from tools import (
    create_confirm_order_tool,
    create_flex_escalation_tool,
    get_available_plans,
    look_up_discounts,
    look_up_order_price,
    look_up_outage,
    run_diagnostic,
)

from taf.models.memory import MemoryRetrievalResponse
from taf.models.session import ConversationSession

logger = logging.getLogger(__name__)


class LLMService:
    """Service for processing messages with LLM using TAF memory context and OpenAI Agents SDK."""

    def __init__(self, taf):
        """
        Initialize LLM service with OpenAI Agents SDK.

        Args:
            taf: TAF instance for accessing Maestro/Memora APIs
        """
        self.taf = taf
        # Base tools that don't need context injection
        self.base_tools = [
            get_available_plans,
            look_up_order_price,
            look_up_discounts,
            look_up_outage,
            run_diagnostic,
        ]

    async def process_message(
        self,
        user_message: str,
        memory_response: MemoryRetrievalResponse | None,
        context: ConversationSession,
        websocket: Optional[WebSocket],
        conversation_history: list[ChatCompletionMessageParam] | None = None,
    ) -> str:
        """
        Process user message with memory context and generate response using Agents SDK.

        Args:
            user_message: The user's message
            memory_response: Memory response from TAF with observations, summaries, and sessions
            context: ConversationSession with conversation details
            websocket: Optional WebSocket connection for voice channel
            conversation_history: Optional conversation history (OpenAI ChatCompletionMessageParam format).
                                 If provided, uses this instead of building from TAF session memories.

        Returns:
            Generated response from LLM
        """
        try:
            # Build TAF-enhanced instructions with profile context
            enhanced_instructions = self._build_enhanced_instructions(memory_response, context)

            # Create context-aware tools dynamically
            tools = self.base_tools + [
                create_confirm_order_tool(self.taf, context),
            ]

            if websocket is not None:
                tools = tools + [create_flex_escalation_tool(websocket)]

            logger.info(f"[LLM] Processing message with {len(tools)} tools available")

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
            logger.info(f"[LLM] Conversation history: {len(previous_messages)} previous messages")

            if previous_messages:
                # Format previous messages as context
                history_lines = [f"{msg['role']}: {msg['content']}" for msg in previous_messages]
                history_context = "\n".join(history_lines)
                agent_input = f"[Previous conversation]\n{history_context}\n\n[Current message]\n{user_message}"
            else:
                # No previous history, just use the current message
                agent_input = user_message

            # Run the agent with the message (tools are executed automatically)
            # Disable tracing to avoid ZDR warnings
            logger.info(f"[AGENT] Running agent with input: {user_message[:50]}...")
            run_config = RunConfig(tracing_disabled=True)
            result = await Runner.run(agent, input=agent_input, run_config=run_config)

            # Extract response
            response = str(result.final_output)
            logger.info("[AGENT] Agent execution completed")

            return response

        except Exception as e:
            logger.error(f"[LLM] Error processing message: {e}", exc_info=True)
            return (
                "I'm sorry, I'm having trouble processing your message right now. Please try again."
            )

    def _build_enhanced_instructions(
        self, memory_response: MemoryRetrievalResponse | None, context: ConversationSession
    ) -> str:
        """
        Build enhanced agent instructions with TAF memory context.

        Args:
            memory_response: Memory response from TAF
            context: ConversationSession with conversation details

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
            f"- Profile ID: {context.profile_id}",
        ]

        # Add profile traits if available
        if context.profile and context.profile.traits:
            # Check for customer name and add special instruction
            customer_name = None
            name_fields = ["name", "firstName"]
            for field in name_fields:
                if field in context.profile.traits and context.profile.traits[field]:
                    customer_name = context.profile.traits[field]
                    break

            if customer_name:
                instruction_parts.append("")
                instruction_parts.append(
                    f"IMPORTANT: The customer's name is {customer_name}. "
                    "Address them by name to personalize the conversation."
                )

            # Add all traits
            logger.info(f"[CONTEXT] Including {len(context.profile.traits)} traits in instructions")
            instruction_parts.append("")
            for trait_key, trait_value in context.profile.traits.items():
                if trait_value is not None:
                    instruction_parts.append(f"- {trait_key}: {trait_value}")
            instruction_parts.append("")

        # Add relevant context from observations
        if memory_response and memory_response.observations:
            logger.info(
                f"[CONTEXT] Including {len(memory_response.observations)} observations in instructions"
            )
            instruction_parts.append("=== RELEVANT OBSERVATIONS (from TAF Memory) ===")
            for obs in memory_response.observations:
                instruction_parts.append(f"- {obs.content}")
            instruction_parts.append("")

        # Add conversation summaries
        if memory_response and memory_response.summaries:
            logger.info(
                f"[CONTEXT] Including {len(memory_response.summaries)} summaries in instructions"
            )
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

        # Add channel-specific formatting instructions
        if context.channel == "voice":
            instruction_parts.extend(
                [
                    "=== IMPORTANT: VOICE/PHONE FORMATTING ===",
                    "This conversation is over the PHONE using text-to-speech.",
                    "- Use PLAIN TEXT ONLY - no markdown formatting",
                    "- Do NOT use asterisks (**bold**), hashtags (#headings), or brackets",
                    "- Do NOT use numbered lists (1. 2. 3.) - say 'first, second, third' instead",
                    "- Do NOT use bullet points (- or *) - speak naturally",
                    "- Speak as you would in a natural phone conversation",
                    "",
                ]
            )
        elif context.channel == "sms":
            instruction_parts.extend(
                [
                    "=== SMS FORMATTING ===",
                    "This conversation is via SMS text message.",
                    "- Use markdown formatting for clarity (bold, lists, etc.)",
                    "- Use **bold** for emphasis on important information",
                    "- Use numbered lists (1. 2. 3.) for multiple options",
                    "- Keep messages concise but well-formatted",
                    "",
                ]
            )

        return "\n".join(instruction_parts)

    def _build_conversation_history(
        self, memory_response: MemoryRetrievalResponse | None
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

        if not memory_response or not memory_response.communications:
            return messages

        # Extract messages from session memories
        for communication in memory_response.communications:
            # Map direction to role (inbound=user, outbound=assistant)
            if communication.author.type == "CUSTOMER":
                user_msg: ChatCompletionUserMessageParam = {
                    "role": "user",
                    "content": communication.content.text or "",
                }
                messages.append(user_msg)
            else:
                assistant_msg: ChatCompletionAssistantMessageParam = {
                    "role": "assistant",
                    "content": communication.content.text or "",
                }
                messages.append(assistant_msg)

        return messages
