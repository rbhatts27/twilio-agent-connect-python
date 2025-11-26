#!/usr/bin/env python3
"""
Simplified Voice Server Example using built-in server

This example demonstrates the simplified VoiceChannel integration with built-in server.
Just provide VoiceServerConfig and call voice_channel.start() - no need to manually
create FastAPI app or routes!

For a manual approach with full control, see examples/channels/voice.py.

Features:
- Automatic server setup with single start() call
- Automatic TwiML and WebSocket endpoint handling
- OpenAI integration for conversational responses
- Memory retrieval and context management
"""

import os
import sys

import openai
from dotenv import load_dotenv
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, VoiceServerConfig, get_logger
from taf.channels.voice import VoiceChannel
from taf.models.memory import MemoryRetrievalResponse
from taf.models.session import ConversationSession

# Initialize logger
logger = get_logger(__name__)

# Global variables
system_prompt = "You're a helpful assistant that helps users over the phone."

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}


async def handle_memory_ready(
    context: ConversationSession, memory_response: MemoryRetrievalResponse, user_message: str
) -> None:
    """
    Callback invoked when memory retrieval completes.

    Processes user message with OpenAI, using retrieved memories for context
    and maintaining conversation history for coherent multi-turn interactions.
    """
    logger.info(f"Processing message for conversation {context.conversation_id}")
    logger.info(
        f"Retrieved memories: {len(memory_response.observations)} observations, "
        f"{len(memory_response.summaries)} summaries, {len(memory_response.sessions)} sessions"
    )

    # Initialize conversation history with system message
    conv_id = context.conversation_id
    if conv_id not in conversation_messages:
        system_msg: ChatCompletionSystemMessageParam = {"role": "system", "content": system_prompt}
        conversation_messages[conv_id] = [system_msg]

    # Add user message to history
    user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
    conversation_messages[conv_id].append(user_msg)

    # Generate response with OpenAI
    client = openai.AsyncOpenAI(api_key=os.environ.get("TWILIO_TAF_OPENAI_API_KEY"))
    completion = await client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_messages[conv_id],
    )

    response = completion.choices[0].message.content

    logger.info("Response generated: %s", response)

    # Send response and update history
    if response:
        assistant_msg: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": response,
        }
        conversation_messages[conv_id].append(assistant_msg)

        await voice_channel.send_response(context.conversation_id, response, role="assistant")


if __name__ == "__main__":
    # Initialize TAF - automatically loads all configuration from environment variables
    # Required env vars:
    #   - TWILIO_TAF_ENVIRONMENT (dev, stage, or prod)
    #   - TWILIO_TAF_CONVERSATION_SERVICE_SID
    #   - TWILIO_TAF_ACCOUNT_SID
    #   - TWILIO_TAF_AUTH_TOKEN
    #   - TWILIO_TAF_PHONE_NUMBER
    # Optional env vars:
    #   - TWILIO_TAF_LOG_LEVEL (defaults to INFO)
    #   - TWILIO_TAF_MEMORY_STORE_ID, TWILIO_TAF_MEMORY_API_KEY, TWILIO_TAF_MEMORY_API_TOKEN (for Twilio Memory)
    #   - TWILIO_TAF_TRAIT_GROUPS (comma-separated, e.g., "Contact,Preferences")
    taf = TAF(config=TAFConfig.from_env())

    # Register callback for memory retrieval
    taf.on_message_ready(handle_memory_ready)

    # Initialize channel with server configuration
    voice_channel = VoiceChannel(
        taf=taf,
        server_config=VoiceServerConfig(
            public_domain=os.environ["TWILIO_TAF_VOICE_PUBLIC_DOMAIN"],
            host="0.0.0.0",
            port=8000,
        ),
    )

    # That's it! Just call start() and everything is handled automatically
    logger.info("Starting simplified voice server...")
    voice_channel.start()
