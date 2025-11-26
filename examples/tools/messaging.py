import asyncio
import json

from agents import Agent, FunctionTool, Runner, Tool
from agents.tool_context import ToolContext
from dotenv import load_dotenv

from taf import TAFConfig
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
    # Load TAF configuration from environment variables
    config = TAFConfig.from_env()

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
