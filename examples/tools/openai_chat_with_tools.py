"""Example: Using TAF tools with OpenAI Chat Completions API"""

import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from taf import TAFConfig
from taf.core.config import TwilioMemoryConfig
from taf.models.session import ConversationSession
from taf.tools.knowledge import create_knowledge_tools_from_ids
from taf.tools.memory import create_memory_tools

# Load environment variables from .env file
load_dotenv(override=True)


async def main() -> None:
    # Initialize TAF
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

    # Create session context (from webhook or conversation flow)
    session = ConversationSession(
        profile_id="mem_profile_00000000000000000000000000",
        conversation_id="conversation_789...",
        channel="sms",
    )

    # Create memory tools with injected config and session
    memory_tools = create_memory_tools(config, session)

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

    # Combine all tools
    all_tools = memory_tools + knowledge_tools

    # Convert TAF tools to OpenAI format
    openai_tools = [tool.to_openai_format() for tool in all_tools]

    # Create tool lookup for execution
    tool_lookup = {tool.name: tool for tool in all_tools}

    # Initialize OpenAI client
    client = AsyncOpenAI()

    messages = [{"role": "user", "content": "Did I order a blue fleece? If so, when?"}]

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
        final_response = await client.chat.completions.create(model="gpt-4", messages=messages)

        print(f"Assistant: {final_response.choices[0].message.content}")
    else:
        print(f"Assistant: {response.choices[0].message.content}")


if __name__ == "__main__":
    asyncio.run(main())
