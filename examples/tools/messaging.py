import asyncio
import json
import os

from agents import Agent, FunctionTool, Runner, Tool
from agents.tool_context import ToolContext
from dotenv import load_dotenv

from taf import TAFConfig
from taf.core.config import TwilioMemoryConfig
from taf.tools import TAFTool
from taf.tools.messaging import create_messaging_tools

# Load environment variables from .env file
load_dotenv(override=True)


def taf_tool_to_agent_tool(taf_tool: TAFTool) -> Tool:
    """Convert TAFTool to OpenAI Agents SDK FunctionTool."""

    async def on_invoke_tool(ctx: ToolContext, args_json: str) -> str:
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
    # Memory service is optional - only include if all required environment variables are set
    memory_store_id = os.getenv("MEMORY_STORE_ID")
    api_key = os.getenv("TWILIO_API_KEY")
    api_token = os.getenv("TWILIO_API_TOKEN")
    twilio_memory_config = (
        TwilioMemoryConfig(memory_store_id=memory_store_id, api_key=api_key, api_token=api_token)
        if memory_store_id and api_key and api_token
        else None
    )

    config = TAFConfig(
        environment=os.getenv("ENVIRONMENT"),
        twilio_memory_config=twilio_memory_config,
        conversation_service_sid=os.getenv("CONVERSATION_SERVICE_SID"),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
        twilio_phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
    )

    agent_tools = [taf_tool_to_agent_tool(x) for x in create_messaging_tools(config)]

    # Create agent with TAF tools
    agent = Agent(
        name="messaging agent",
        model="gpt-4o",
        tools=agent_tools,
        instructions="You are a helpful assistant",
    )

    # Use the agent
    response = await Runner.run(
        agent, "Send a message to +12345678900 saying 'Hello from TAF agent!'"
    )
    print(f"Agent response: {response}")


if __name__ == "__main__":
    asyncio.run(main())
