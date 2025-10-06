"""Example: Using TAF tools with OpenAI Agents SDK"""

import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv

from taf import TAFConfig
from taf.core.context import ConversationSession
from taf.tools.memory import create_memory_tools

# Load environment variables from .env file
load_dotenv(override=True)

# This example requires: pip install openai-agents
from agents import Agent, FunctionTool, Runner


def taf_tool_to_openai_agents(taf_tool: Any) -> Any:
    """Convert TAFTool to OpenAI Agents SDK FunctionTool."""

    async def on_invoke_tool(ctx: Any, args_json: str) -> str:
        """Handle tool invocation from OpenAI Agents SDK."""
        args = json.loads(args_json)
        result = taf_tool.implementation(**args)
        return json.dumps(result) if not isinstance(result, str) else result

    return FunctionTool(
        name=taf_tool.name,
        description=taf_tool.description,
        params_json_schema=taf_tool.params_json_schema,
        on_invoke_tool=on_invoke_tool,
    )


async def main() -> None:
    # Initialize TAF
    config = TAFConfig(
        memora_base_url=os.getenv("MEMORA_BASE_URL"),
        memory_service_sid=os.getenv("MEMORY_SERVICE_SID"),
        maestro_base_url=os.getenv("MAESTRO_BASE_URL"),
        conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
    )

    # Create session context
    session = ConversationSession(
        profile_id="mem_profile_00000000000000000000000000",
        conversation_id="conversation_789...",
        channel="sms",
    )

    # Create TAF tools with injected config
    memory_tools = create_memory_tools(config, session)
    print(f"memory_tools: {memory_tools}")

    # Convert TAF tools to OpenAI Agents SDK format
    openai_agent_tools = [taf_tool_to_openai_agents(tool) for tool in memory_tools]
    print(f"openai_agent_tools: {openai_agent_tools}")

    # Create agent with TAF tools
    agent = Agent(
        name="memory_agent",
        model="gpt-4",
        tools=openai_agent_tools,
        instructions="You are a helpful assistant that can search user memories to provide personalized responses.",
    )

    # Use the agent
    response = await Runner.run(agent, "Did I order a blue fleece? If so, when?")
    print(f"Agent response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
