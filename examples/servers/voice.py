#!/usr/bin/env python3
"""
Voice Server for Twilio Agentic Framework

Example demonstrating VoiceChannel with FastAPI server for TwiML and WebSocket endpoints.
"""

import os
import sys

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

# Add parent directory to path to import taf
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from taf import TAF, TAFConfig, get_logger
from taf.channels.voice import VoiceChannel
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalResponse

# Initialize logger
logger = get_logger(__name__)

# Global variables
voice_channel: VoiceChannel
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
    client = openai.AsyncOpenAI()
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
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
    # Initialize TAF
    taf = TAF(
        config=TAFConfig(
            environment=os.environ["ENVIRONMENT"],
            memory_service_sid=os.environ["MEMORY_SERVICE_SID"],
            conversation_service_sid=os.environ["CONVERSATION_SERVICE_SID"],
            twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
            twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
            twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
        )
    )

    # Register callback for memory retrieval
    taf.on_memory_ready(handle_memory_ready)

    # Initialize channel
    voice_channel = VoiceChannel(taf=taf)

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
            conversation_id="fake_id",  # todo: resolve id when maestro is ready
        )
        return Response(content=twiml, media_type="application/xml")

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """Handle voice WebSocket connections for real-time streaming."""
        await voice_channel.handle_websocket(websocket)

    # Start the server
    logger.info("Starting TAF Voice Server on 0.0.0.0:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
