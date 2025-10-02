"""Example: Using TAF tools with OpenAI Chat Completions API"""

import asyncio
import json

from openai import AsyncOpenAI

from taf import TAF, TAFConfig
from taf.core.context import SessionIdentity
from taf.tools.memory import create_memory_tools


async def main() -> None:
    # Initialize TAF
    config = TAFConfig(
        memora_base_url="https://memora.twilio.com/v1",
        memora_auth_token="your_memora_token",
        memory_service_sid="mem_service_123...",
        maestro_base_url="https://maestro.twilio.com/v1",
        twilio_account_sid="AC123...",
        conversation_service_sid="IS123...",
    )

    # Create session context (from webhook or conversation flow)
    session = SessionIdentity(
        profile_id="profile_456...", conversation_id="conversation_789..."
    )

    # Create TAF tools with injected config
    memory_tools = create_memory_tools(config, session)

    # Convert TAF tools to OpenAI format
    openai_tools = [tool.to_openai_format() for tool in memory_tools]

    # Create tool lookup for execution
    tool_lookup = {tool.name: tool for tool in memory_tools}

    # Initialize OpenAI client
    client = AsyncOpenAI(api_key="your_openai_key")

    messages = [{"role": "user", "content": "What are my food preferences?"}]

    # First API call with tools
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=openai_tools,  # TAF tools converted to OpenAI format
        tool_choice="auto",
    )

    # Check if model wants to call tools
    if response.choices[0].message.tool_calls:
        messages.append(response.choices[0].message)

        # Execute each tool call
        for tool_call in response.choices[0].message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            # Execute TAF tool
            if tool_name in tool_lookup:
                taf_tool = tool_lookup[tool_name]
                try:
                    result = taf_tool.implementation(**tool_args)
                    tool_result = json.dumps(result)
                except Exception as e:
                    tool_result = f"Error: {str(e)}"

                # Add tool result to conversation
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )

        # Second API call with tool results
        final_response = await client.chat.completions.create(
            model="gpt-4", messages=messages
        )

        print(f"Assistant: {final_response.choices[0].message.content}")
    else:
        print(f"Assistant: {response.choices[0].message.content}")


if __name__ == "__main__":
    asyncio.run(main())
