"""
LLM Service for All My Sons Moving & Storage Demo

This module provides an LLM service that processes messages with context from TAC memory.
It builds enhanced system prompts with customer profile information and moving context.
Uses OpenAI Agents SDK for tool integration and conversation management.

Key features for Anchor 1 (Concurrent Cross-Channel):
- Handles both voice and SMS messages in the same conversation
- Provides channel-specific formatting (voice=natural speech, SMS=formatted text)
- Integrates photo analysis results into quote calculations
- Manages concurrent channel context
"""

import logging
import os
from typing import Optional

from agents import Agent, RunConfig, Runner, set_default_openai_key
from business_data import COMPANY_INFO
from fastapi import WebSocket
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)
from tools import (
    analyze_furniture_photo,
    calculate_move_quote,
    create_acknowledge_photo_sms_tool,
    create_send_quote_sms_tool,
    get_company_info,
    get_insurance_options,
    get_packing_options,
    get_storage_options,
)

from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

logger = logging.getLogger(__name__)


class LLMService:
    """Service for processing messages with LLM using TAC memory context and OpenAI Agents SDK."""

    def __init__(self, tac):
        """
        Initialize LLM service with OpenAI Agents SDK.

        Args:
            tac: TAC instance for accessing Maestro/Memora APIs
        """
        self.tac = tac
        # Configure OpenAI API key for Agents SDK
        openai_api_key = os.environ.get("TWILIO_TAC_OPENAI_API_KEY")
        if openai_api_key:
            set_default_openai_key(openai_api_key)

        # Base tools that don't need context injection
        self.base_tools = [
            analyze_furniture_photo,
            calculate_move_quote,
            get_insurance_options,
            get_storage_options,
            get_company_info,
            get_packing_options,
        ]

    async def process_message(
        self,
        user_message: str,
        memory_response: MemoryRetrievalResponse | None,
        context: ConversationSession,
        websocket: Optional[WebSocket],
        conversation_history: list[ChatCompletionMessageParam] | None = None,
        incoming_channel: str | None = None,
    ) -> str:
        """
        Process user message with memory context and generate response using Agents SDK.

        Args:
            user_message: The user's message
            memory_response: Memory response from TAC with observations, summaries, and sessions
            context: ConversationSession with conversation details
            websocket: Optional WebSocket connection for voice channel
            conversation_history: Optional conversation history (OpenAI ChatCompletionMessageParam format)
            incoming_channel: The channel the current message came from (may differ from primary)

        Returns:
            Generated response from LLM
        """
        try:
            # Determine the actual channel for this message
            message_channel = incoming_channel or context.channel

            # Build TAC-enhanced instructions with profile context
            enhanced_instructions = self._build_enhanced_instructions(
                memory_response, context, message_channel
            )

            # Create context-aware tools dynamically
            tools = self.base_tools.copy()

            # Add SMS tools for sending quotes and acknowledgments
            tools.append(create_send_quote_sms_tool(self.tac, context))
            tools.append(create_acknowledge_photo_sms_tool(self.tac, context))

            logger.info(f"[LLM] Processing {message_channel} message with {len(tools)} tools available")

            # Create agent with TAC-enhanced instructions
            agent = Agent(
                name="All My Sons Moving Assistant",
                instructions=enhanced_instructions,
                model="gpt-4o",
                tools=tools,
            )

            # Use passed conversation history if provided, otherwise build from TAC session memories
            if conversation_history is not None:
                messages_history = conversation_history
            else:
                messages_history = self._build_conversation_history(memory_response)

            # Format conversation history for agent context
            # Exclude the current user message to avoid duplication
            previous_messages = messages_history[:-1] if messages_history else []
            logger.info(f"[LLM] Conversation history: {len(previous_messages)} previous messages")

            if previous_messages:
                history_lines = [f"{msg['role']}: {msg['content']}" for msg in previous_messages]
                history_context = "\n".join(history_lines)
                agent_input = f"[Previous conversation]\n{history_context}\n\n[Current message from {message_channel.upper()}]\n{user_message}"
            else:
                agent_input = f"[Message from {message_channel.upper()}]\n{user_message}"

            # Run the agent with the message
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
                "I'm sorry, I'm having trouble processing your request right now. "
                "Please try again or call us at 1-800-ALL-SONS for immediate assistance."
            )

    def _build_enhanced_instructions(
        self,
        memory_response: MemoryRetrievalResponse | None,
        context: ConversationSession,
        message_channel: str,
    ) -> str:
        """
        Build enhanced agent instructions with TAC memory context.

        Args:
            memory_response: Memory response from TAC
            context: ConversationSession with conversation details
            message_channel: The channel the current message is from

        Returns:
            Enhanced instructions string for the agent
        """
        instruction_parts = [
            f"You are a friendly, knowledgeable moving consultant for {COMPANY_INFO['name']}.",
            f"Our tagline: '{COMPANY_INFO['tagline']}'",
            "",
            "Your role is to help customers get accurate moving quotes by gathering information",
            "about their move: origin, destination, home size, and special items.",
            "",
            "=== CONCURRENT CHANNEL AWARENESS ===",
            f"Primary conversation channel: {context.channel.upper()}",
            f"Current message is from: {message_channel.upper()}",
            "",
            "CRITICAL: You are managing a conversation that may span BOTH voice and SMS simultaneously.",
            "- If customer is on a VOICE call and sends an SMS (like a photo), acknowledge it verbally",
            "- You can send SMS messages while on voice call using the send_quote_sms tool",
            "- You can acknowledge photo receipt via SMS using acknowledge_photo_sms tool",
            "- Keep voice responses conversational, SMS responses can be formatted",
            "",
        ]

        # Add profile information if available
        if context.profile_id:
            instruction_parts.extend([
                "=== CUSTOMER PROFILE ===",
                f"Profile ID: {context.profile_id}",
            ])

            if context.profile and context.profile.traits:
                customer_name = None
                for field in ["name", "firstName", "first_name"]:
                    if field in context.profile.traits and context.profile.traits[field]:
                        customer_name = context.profile.traits[field]
                        break

                if customer_name:
                    instruction_parts.append("")
                    instruction_parts.append(
                        f"IMPORTANT: The customer's name is {customer_name}. "
                        "Use their name naturally in conversation to personalize the experience."
                    )

                instruction_parts.append("")
                for trait_key, trait_value in context.profile.traits.items():
                    if trait_value is not None:
                        instruction_parts.append(f"- {trait_key}: {trait_value}")
                instruction_parts.append("")

        # Add relevant observations from memory
        if memory_response and memory_response.observations:
            instruction_parts.extend([
                "=== CUSTOMER HISTORY (from Memory) ===",
                "Previous interactions and preferences:"
            ])
            for obs in memory_response.observations:
                instruction_parts.append(f"- {obs.content}")
            instruction_parts.append("")

        # Add conversation summaries
        if memory_response and memory_response.summaries:
            instruction_parts.extend([
                "=== PREVIOUS CONVERSATION SUMMARIES ===",
            ])
            for summary in memory_response.summaries:
                instruction_parts.append(f"- {summary.content}")
            instruction_parts.append("")

        # Quote process instructions
        instruction_parts.extend([
            "=== QUOTE PROCESS ===",
            "To provide an accurate quote, you need:",
            "1. Origin address (city, state)",
            "2. Destination address (city, state)",
            "3. Home size (bedrooms or square footage)",
            "4. Any special items (pianos, antiques, pool tables, etc.)",
            "",
            "PHOTO WORKFLOW:",
            "- Ask customer to text photos of their furniture, especially large/special items",
            "- When they send photos, use analyze_furniture_photo to identify items",
            "- Send SMS acknowledgment immediately: 'Got your photo! Analyzing now...'",
            "- Continue voice conversation with photo analysis results",
            "- Use identified items to calculate accurate quote",
            "",
            "QUOTE DELIVERY:",
            "- Calculate quote using calculate_move_quote tool",
            "- Verbally give the estimate range on voice call",
            "- Send detailed breakdown via SMS using send_quote_sms tool",
            "- Ask if they have questions about any line items",
            "",
        ])

        # Channel-specific formatting
        if message_channel == "voice":
            instruction_parts.extend([
                "=== VOICE FORMATTING (Current Message) ===",
                "This message is from a PHONE CALL using text-to-speech.",
                "- Use PLAIN TEXT ONLY - no markdown, asterisks, or special formatting",
                "- Speak naturally as you would on a phone call",
                "- Say numbers clearly: 'four thousand two hundred dollars' not '$4,200'",
                "- Keep responses concise but warm and helpful",
                "- Pause naturally between topics",
                "",
            ])
        elif message_channel == "sms":
            instruction_parts.extend([
                "=== SMS FORMATTING (Current Message) ===",
                "This message is from SMS text messaging.",
                "- Use markdown formatting for clarity",
                "- Use **bold** for important numbers and totals",
                "- Use bullet points for lists",
                "- Keep messages focused and scannable",
                "- If this is a photo description, acknowledge and analyze",
                "",
            ])

        # Behavioral guidelines
        instruction_parts.extend([
            "=== BEHAVIOR GUIDELINES ===",
            "1. Be warm, friendly, and reassuring - moving is stressful!",
            "2. Proactively offer to help with special items and concerns",
            "3. Explain pricing clearly - no surprises",
            "4. If customer seems overwhelmed, offer to slow down or call back",
            "5. Always recommend appropriate insurance for valuable items",
            "6. Mention storage options if there's a gap between move dates",
            "",
            f"Company Contact: {COMPANY_INFO['phone']} | {COMPANY_INFO['email']}",
            f"Hours: {COMPANY_INFO['hours']}",
            "",
        ])

        return "\n".join(instruction_parts)

    def _build_conversation_history(
        self, memory_response: MemoryRetrievalResponse | None
    ) -> list[ChatCompletionMessageParam]:
        """
        Build conversation history from session memories.

        Args:
            memory_response: Memory response from TAC

        Returns:
            List of OpenAI ChatCompletionMessageParam
        """
        messages: list[ChatCompletionMessageParam] = []

        if not memory_response or not memory_response.communications:
            return messages

        for communication in memory_response.communications:
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
