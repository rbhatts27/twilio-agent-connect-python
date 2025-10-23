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

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.voice import VoiceChannel
from taf.context.memory import MemoryRetrievalResponse
from taf.core.context import ConversationSession

# Initialize logger
logger = get_logger(__name__)

# Global variables
voice_channel: VoiceChannel
system_prompt = "You're a helpful assistant that helps users over the phone."


async def handle_memory_ready(
    context: ConversationSession, memory_response: MemoryRetrievalResponse, user_message: str
) -> None:
    """
    Callback invoked when memory retrieval completes.

    This demonstrates how to process memories and respond to messages.
    Uses openai-agents SDK for agent-based responses.
    """
    logger.info(f"User message: {user_message}")

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
    if response:
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

    # Create FastAPI app
    app = FastAPI(title="TAF Voice Server")

    @app.get("/twiml")
    async def get_twiml() -> Response:
        """Generate TwiML for Twilio voice calls."""
        public_domain = os.environ.get("VOICE_PUBLIC_DOMAIN", "")
        websocket_url = f"wss://{public_domain}/ws"
        twiml = voice_channel.handle_incoming_call(websocket_url=websocket_url)
        return Response(content=twiml, media_type="application/xml")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle voice streaming WebSocket connection."""
        await voice_channel.handle_websocket(websocket)

    # Start the server
    logger.info("Starting TAF Voice Server on 0.0.0.0:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
