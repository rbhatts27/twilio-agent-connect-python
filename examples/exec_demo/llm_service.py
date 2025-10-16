"""
LLM Service for TAF SMS Demo

This module provides an LLM service that processes messages with context from TAF memory.
It builds enhanced system prompts with customer profile information and conversation history.
Uses OpenAI Agents SDK for tool integration and conversation management.
"""

import logging

from agents import Agent, Runner

from taf.context.memory import TwilioMemory

# Import tools from tools.py
from .tools import confirm_order, look_up_discounts, look_up_order_price

logger = logging.getLogger(__name__)


class LLMService:
    """Service for processing messages with LLM using TAF memory context and OpenAI Agents SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
    ):
        """
        Initialize LLM service with OpenAI Agents SDK.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.api_key = api_key
        self.model = model
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
        memories: list[TwilioMemory],
        profile_id: str,
    ) -> str:
        """
        Process user message with memory context and generate response using Agents SDK.

        Args:
            user_message: The user's message
            memories: List of memories from TAF (traits, observations, sessions)
            profile_id: User's profile ID

        Returns:
            Generated response from LLM
        """
        try:
            # Build TAF-enhanced instructions with profile context
            enhanced_instructions = self._build_enhanced_instructions(memories, profile_id)

            # Create agent with TAF-enhanced instructions
            agent = Agent(
                name="Owl Internet Customer Service",
                instructions=enhanced_instructions,
                model=self.model,
                tools=self.tools,
            )

            # Build conversation history from TAF session memories
            messages_history = self._build_conversation_history(memories)

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

    def _build_enhanced_instructions(self, memories: list[TwilioMemory], profile_id: str) -> str:
        """
        Build enhanced agent instructions with TAF memory context.

        Args:
            memories: List of memories from TAF
            profile_id: User's profile ID

        Returns:
            Enhanced instructions string for the agent
        """
        # Group memories by type (exclude sessions - they're handled as conversation history)
        traits = [m for m in memories if m.mem_type == "TRAIT"]
        observations = [m for m in memories if m.mem_type == "OBSERVATION"]

        # Extract specific traits into a dictionary for easy access
        trait_dict = {trait.name: trait.value for trait in traits}

        # Build instructions parts
        instruction_parts = [
            "You are Owl Internet's comprehensive customer service assistant.",
            "Your goal is to provide personalized, helpful support using the customer's profile "
            "and interaction history.",
            "",
        ]

        # Add customer profile section
        instruction_parts.append("=== CUSTOMER PROFILE (from TAF Memora) ===")

        if traits:
            # Extract key profile information
            customer_name = trait_dict.get("name", "Valued Customer")
            plan_name = trait_dict.get("plan_name", "Unknown Plan")
            account_status = trait_dict.get("account_status", "unknown")
            loyalty_tier = trait_dict.get("loyalty_tier", "standard")
            customer_since = trait_dict.get("customer_since", "Unknown")
            comm_pref = trait_dict.get("communication_preference", "not specified")

            instruction_parts.extend(
                [
                    f"- Customer Name: {customer_name}",
                    f"- Profile ID: {profile_id}",
                    f"- Service Plan: {plan_name}",
                    f"- Account Status: {account_status}",
                    f"- Loyalty Tier: {loyalty_tier}",
                    f"- Customer Since: {customer_since}",
                    f"- Communication Preference: {comm_pref}",
                    "",
                ]
            )

            # Add any additional traits not covered above
            standard_traits = {
                "name",
                "plan_name",
                "account_status",
                "loyalty_tier",
                "customer_since",
                "communication_preference",
            }
            additional_traits = {k: v for k, v in trait_dict.items() if k not in standard_traits}
            if additional_traits:
                instruction_parts.append("Additional Profile Details:")
                for trait_name, trait_value in additional_traits.items():
                    instruction_parts.append(f"  - {trait_name}: {trait_value}")
                instruction_parts.append("")
        else:
            instruction_parts.extend(
                [f"- Profile ID: {profile_id}", "- No profile traits available", ""]
            )

        # Add relevant context from observations
        if observations:
            instruction_parts.append("=== RELEVANT CONTEXT (from TAF Contextual Memory) ===")
            for obs in observations:
                instruction_parts.append(f"- {obs.content}")
            instruction_parts.append("")

        # Add TAF-enhanced behavioral instructions
        instruction_parts.extend(
            [
                "=== TAF-ENHANCED BEHAVIOR ===",
                "1. PERSONALIZATION:",
                "   - Address the customer by name when appropriate",
                "   - Reference their service plan and account details naturally in responses",
                "   - Acknowledge their loyalty tier and tenure when relevant",
                "",
                "2. CONTEXT AWARENESS:",
                "   - Use the conversation history to maintain continuity",
                "   - Reference previous observations to show you remember past interactions",
                "   - Avoid asking for information already in their profile",
                "",
                "3. COMMUNICATION STYLE:",
                "   - Match the customer's communication preference when specified",
                "   - Keep responses clear, concise, and professional",
                "   - Show empathy and understanding of their situation",
                "",
                "4. SERVICE EXCELLENCE:",
                "   - Provide proactive suggestions based on their service plan",
                "   - Offer relevant upgrades or features for their loyalty tier",
                "   - Ensure account status is considered in recommendations",
                "   - If you need more information to help, ask specific clarifying questions",
                "",
            ]
        )

        return "\n".join(instruction_parts)

    def _build_conversation_history(self, memories: list[TwilioMemory]) -> list[dict]:
        """
        Build conversation history from session memories.

        Session memories contain previous conversation exchanges.

        Args:
            memories: List of memories from TAF

        Returns:
            List of message dicts with role and content
        """
        messages = []

        # Extract session memories (conversation history)
        sessions = [m for m in memories if m.mem_type == "SESSION"]

        for session in sessions:
            # Session memories typically contain conversation exchanges
            # Format: "User: <message>\nAssistant: <response>"
            # or just the content directly
            content = session.content

            # Try to parse structured conversation format
            if "\nAssistant:" in content or "\nUser:" in content:
                # Split by turns
                parts = content.split("\n")
                for part in parts:
                    if part.startswith("User:"):
                        messages.append(
                            {"role": "user", "content": part.replace("User:", "").strip()}
                        )
                    elif part.startswith("Assistant:"):
                        messages.append(
                            {
                                "role": "assistant",
                                "content": part.replace("Assistant:", "").strip(),
                            }
                        )
            else:
                # If no structured format, treat as user message
                # (This is a fallback - actual format depends on Memora storage)
                messages.append({"role": "user", "content": content})

        return messages
