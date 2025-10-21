#!/usr/bin/env python3
"""
Voice Server for Twilio Agentic Framework

Example demonstrating VoiceChannel with FastAPI server for TwiML and WebSocket endpoints.
"""

import os
import sys
from typing import cast

import openai
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.voice import VoiceChannel
from taf.context.memory import MemoryRetrievalResponse
from taf.core.context import ConversationSession


class RelayConfiguration(BaseModel):
    """
    Configuration for Voice channel ConversationRelay server.

    Attributes:
        public_domain: Public domain for TwiML (required, e.g., "abc123.ngrok.io")
        host: Host to bind server (default: "0.0.0.0")
        port: Port for server (default: 8000)
        welcome_greeting: Greeting message for incoming calls
    """

    public_domain: str = Field(..., description="Public domain for TwiML (e.g., 'abc123.ngrok.io')")
    host: str = Field(default="0.0.0.0", description="Host to bind server")
    port: int = Field(default=8000, description="Port for server", gt=0, lt=65536)
    welcome_greeting: str = Field(
        default="Hello! How can I assist you today?",
        description="Greeting message for incoming calls",
    )


# Initialize logger
logger = get_logger(__name__)

# Global variables
voice_channel = None
system_prompt = "You're a helpful assistant that helps users over the phone."


async def handle_memory_ready(
    context: ConversationSession, memory_response: MemoryRetrievalResponse, user_message: str
) -> None:
    """
    Callback invoked when memory retrieval completes.

    This demonstrates how to process memories and respond to messages.
    Uses openai-agents SDK for agent-based responses.
    """
    logger.info(
        f"Memory ready for conversation {context.conversation_id} on channel {context.channel}"
    )
    logger.info(f"Profile ID: {context.profile_id}")
    logger.info(f"User message: {user_message}")
    logger.info(f"Retrieved {len(memory_response.observations)} observations")
    logger.info(f"Retrieved {len(memory_response.summaries)} summaries")
    logger.info(f"Retrieved {len(memory_response.sessions)} sessions")

    # Log memory details
    for obs in memory_response.observations:
        logger.info(f"  - Observation: {obs.content[:100]}...")  # Truncate for readability

    for summary in memory_response.summaries:
        logger.info(f"  - Summary: {summary.content[:100]}...")  # Truncate for readability

    for session in memory_response.sessions:
        logger.info(f"  - Session memory: {len(session.messages)} messages")

    # Build messages array with system prompt and conversation history
    messages: list[ChatCompletionMessageParam] = [
        cast(ChatCompletionMessageParam, cast(object, {"role": "system", "content": system_prompt}))
    ] + cast(list[ChatCompletionMessageParam], cast(object, context.messages))

    client = openai.AsyncOpenAI()
    # todo: pass context data to model
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
    )

    response = completion.choices[0].message.content

    # Send response through the voice channel
    if response and voice_channel:
        await voice_channel.send_response(context.conversation_id, response, role="assistant")


if __name__ == "__main__":
    # Initialize TAF with environment variables (will raise KeyError if missing)
    taf = TAF(
        config=TAFConfig(
            memora_base_url=os.environ["MEMORA_BASE_URL"],
            memory_service_sid=os.environ["MEMORY_SERVICE_SID"],
            maestro_base_url=os.environ["MAESTRO_BASE_URL"],
            conversation_service_sid=os.environ["CONVERSATION_SERVICE_SID"],
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
        )
    )

    # Register memory ready callback
    taf.on_memory_ready(handle_memory_ready)

    # Create voice channel (protocol handler only, no server)
    voice_channel = VoiceChannel(taf=taf)

    # Create relay configuration
    relay_config = RelayConfiguration(
        public_domain=os.environ["VOICE_PUBLIC_DOMAIN"],
        host="0.0.0.0",
        port=8000,
        welcome_greeting="Hello! How can I assist you today?",
    )

    # Create FastAPI app
    app = FastAPI(title="TAF Voice Server")

    @app.get("/twiml")
    async def get_twiml() -> Response:
        """Generate TwiML for Twilio voice calls."""
        # Create conversation for this call
        conversation = taf.maestro_client.create_conversation()

        # Build websocket URL using public domain
        websocket_url = f"wss://{relay_config.public_domain}/ws"

        # Generate TwiML response
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <ConversationRelay
            url="{websocket_url}"
            welcomeGreeting="{relay_config.welcome_greeting}"
            debug="debugging">
            <Parameter name="conversationId" value="{conversation.id}" />
        </ConversationRelay>
    </Connect>
</Response>"""

        return Response(content=twiml, media_type="application/xml")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle voice streaming WebSocket connection."""
        await voice_channel.handle_websocket(websocket)

    # Start the server
    logger.info(f"Starting TAF Voice Server on {relay_config.host}:{relay_config.port}")
    logger.info("Available routes:")
    logger.info(f"  GET  http://{relay_config.host}:{relay_config.port}/twiml")
    logger.info(f"  WS   ws://{relay_config.host}:{relay_config.port}/ws")

    uvicorn.run(app, host=relay_config.host, port=relay_config.port, log_level="info")
