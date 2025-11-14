#!/usr/bin/env python3
"""
Voice Channel Example with Session Management and Streaming

This example demonstrates VoiceChannel integration with FastAPI using session management
to handle interrupts and cancel in-flight streaming tasks.

Features:
- Voice call handling with TwiML generation
- WebSocket connection for real-time voice streaming
- OpenAI GPT-4o streaming integration for conversational responses
- Session management for handling interrupts and task cancellation
- Memory retrieval and context management
"""

import os
import sys
from collections.abc import AsyncGenerator

import openai
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, WebSocket
from fastapi.responses import Response
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging based on LOG_LEVEL environment variable
import logging

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.session_manager import ThreadSafeSessionManager
from taf.channels.voice import VoiceChannel
from taf.core.config import TwilioMemoryConfig

# Initialize logger
logger = get_logger(__name__)

# Global variables
voice_channel: VoiceChannel
system_prompt = "Hi! I am a TAF voice expert. Ask me anything"


# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}


async def stream_openai_response(prompt: str, session_id: str) -> AsyncGenerator[str, None]:
    """
    Stream generator that yields OpenAI GPT-4o streaming chunks.

    Args:
        prompt: The user's message to send to OpenAI
        session_id: The conversation/session ID for maintaining history

    Yields:
        Text chunks from the OpenAI streaming response
    """
    logger.info(f"Streaming response for session {session_id}")

    # Initialize conversation history with system message if needed
    if session_id not in conversation_messages:
        system_msg: ChatCompletionSystemMessageParam = {"role": "system", "content": system_prompt}
        conversation_messages[session_id] = [system_msg]

    # Add user message to history
    user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": prompt}
    conversation_messages[session_id].append(user_msg)

    # Stream response from OpenAI
    client = openai.AsyncOpenAI()
    stream = await client.chat.completions.create(
        model="gpt-4o",
        messages=conversation_messages[session_id],
        stream=True,
    )

    full_response = ""
    async for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            full_response += content
            yield content

    # Add assistant response to history
    if full_response:
        assistant_msg: ChatCompletionAssistantMessageParam = {
            "role": "assistant",
            "content": full_response,
        }
        conversation_messages[session_id].append(assistant_msg)
        logger.info(f"Completed streaming response for session {session_id}")


if __name__ == "__main__":
    # Initialize TAF
    # Memory service is optional - only include if all required environment variables are set
    memory_store_id = os.environ.get("MEMORY_STORE_ID")

    # Trait groups are optional - specify which trait groups to retrieve
    # Example: TRAIT_GROUPS="Contact,Preferences" or leave unset for all groups
    trait_groups_str = os.environ.get("TRAIT_GROUPS")
    trait_groups = [g.strip() for g in trait_groups_str.split(",")] if trait_groups_str else None

    api_key = os.environ.get("TWILIO_API_KEY")
    api_token = os.environ.get("TWILIO_API_TOKEN")
    twilio_memory_config = (
        TwilioMemoryConfig(
            memory_store_id=memory_store_id,
            trait_groups=trait_groups,
            api_key=api_key,
            api_token=api_token,
        )
        if memory_store_id and api_key and api_token
        else None
    )

    taf = TAF(
        config=TAFConfig(
            environment=os.environ["ENVIRONMENT"],
            twilio_memory_config=twilio_memory_config,
            conversation_service_sid=os.environ["CONVERSATION_SERVICE_SID"],
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
        )
    )

    # Initialize session manager with OpenAI streaming
    session_manager = ThreadSafeSessionManager(stream_generator=stream_openai_response)

    # Initialize VoiceChannel with session management enabled
    voice_channel = VoiceChannel(taf=taf, session_manager=session_manager)

    # Debug: Verify session manager is set
    logger.info(
        f"VoiceChannel initialized with session_manager: {voice_channel.session_manager is not None}"
    )

    # Create FastAPI app
    app = FastAPI(title="TAF Voice Server")

    @app.post("/twiml")
    async def post_twiml(From: str = Form(...)) -> Response:
        """Generate TwiML for incoming voice calls."""
        public_domain = os.environ.get("VOICE_PUBLIC_DOMAIN")
        websocket_url = f"wss://{public_domain}/ws"

        twiml = voice_channel.handle_incoming_call(
            websocket_url=websocket_url,
            called_phone_number=From,
            welcome_greeting="Hello! How can I assist you today?",
        )
        return Response(content=twiml, media_type="application/xml")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle voice WebSocket connections for real-time streaming."""
        await voice_channel.handle_websocket(websocket)

    # Start the server
    logger.info("Starting TAF Voice Server on 0.0.0.0:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
