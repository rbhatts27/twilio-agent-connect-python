"""Example: Using TAF tools with OpenAI Agents SDK"""

import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv

from taf import TAFConfig
from taf.core.context import ConversationSession
from taf.tools.knowledge import create_knowledge_tools_from_ids
from taf.tools.memory import create_memory_tools

# Load environment variables from .env file
load_dotenv(override=True)

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
        environment=os.getenv("ENVIRONMENT"),
        conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
        memory_service_sid=os.getenv("MEMORY_SERVICE_SID"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
    )

    # Create session context
    session = ConversationSession(
        profile_id="mem_profile_00000000000000000000000000",
        conversation_id="conversation_789...",
        channel="sms",
    )

    # Create memory tools with injected config and session
    memory_tools = create_memory_tools(config, session)
    print(f"memory_tools: {memory_tools}")

    # Create knowledge tools from environment variable
    # KNOWLEDGE_IDS should be a comma-separated list of knowledge IDs (e.g., "KN123,KN456")
    knowledge_ids_str = os.getenv("KNOWLEDGE_IDS", "")
    knowledge_tools = []
    if knowledge_ids_str:
        knowledge_ids = [kid.strip() for kid in knowledge_ids_str.split(",")]
        # Optional: Customize specific tools via tool_configs
        tool_configs = {
            # Example: Override tool name and top_k for specific knowledge
            # "KN456": KnowledgeToolConfig(name="search_return_policy", top_k=3),
        }
        knowledge_tools = create_knowledge_tools_from_ids(config, knowledge_ids, tool_configs)
    print(f"knowledge_tools: {knowledge_tools}")

    # Combine all tools
    all_tools = memory_tools + knowledge_tools
    print(f"all_tools: {all_tools}")

    # Convert TAF tools to OpenAI Agents SDK format
    openai_agent_tools = [taf_tool_to_openai_agents(tool) for tool in all_tools]
    print(f"openai_agent_tools: {openai_agent_tools}")

    # Create agent with TAF tools (memory + knowledge)
    agent = Agent(
        name="support_agent",
        model="gpt-4",
        tools=openai_agent_tools,
        instructions=(
            "You are a helpful customer support assistant. "
            "You can search the user's conversation history and preferences using memory tools, "
            "and answer questions using our product documentation and policies via knowledge tools. "
            "Provide personalized and accurate responses."
        ),
    )

    # Use the agent
    response = await Runner.run(agent, "Did I order a blue fleece? If so, when?")
    print(f"Agent response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
