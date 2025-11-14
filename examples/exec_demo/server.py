"""
TAF Multi-Channel Demo - Executable Example

A complete multi-channel demo showing how to:
1. Set up TAF with SMS and Voice channels
2. Process webhooks from Twilio (SMS and Voice)
3. Retrieve memories and context
4. Process messages with LLM (OpenAI)
5. Send responses back through SMS and Voice
6. Handle WebSocket connections for Voice streaming

This demo demonstrates TAF's channel-agnostic architecture with both SMS and Voice support.
"""

import logging
import os
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, WebSocket
from fastapi.responses import Response
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from taf import TAF, TAFConfig
from taf.channels.voice import VoiceChannel
from taf.core.config import TwilioMemoryConfig
from taf.core.context import ConversationSession
from taf.models.memory import MemoryRetrievalResponse

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="TAF Multi-Channel Demo",
    description="Multi-channel demo using Twilio Agentic Framework",
    version="1.0.0",
)

# Initialize TAF configuration
memory_store_id = os.getenv("MEMORY_STORE_ID")
api_key = os.getenv("TWILIO_API_KEY")
api_token = os.getenv("TWILIO_API_TOKEN")
twilio_memory_config = (
    TwilioMemoryConfig(memory_store_id=memory_store_id, api_key=api_key, api_token=api_token)
    if memory_store_id and api_key and api_token
    else None
)

taf_config = TAFConfig(
    environment=os.environ["ENVIRONMENT"],
    twilio_account_sid=os.environ["TWILIO_ACCOUNT_SID"],
    twilio_auth_token=os.environ["TWILIO_AUTH_TOKEN"],
    twilio_phone_number=os.environ["TWILIO_PHONE_NUMBER"],
    twilio_memory_config=twilio_memory_config,
    conversation_service_sid=os.environ["CONVERSATION_SERVICE_SID"],
)

taf = TAF(config=taf_config)
voice_channel = VoiceChannel(taf)

llm_service = LLMService(taf)

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}
# todo: use a global conversation id until vnext is ready
active_conversation_sid = None


# Register message ready callback
async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
) -> None:
    """
    Callback invoked when a message is ready to be processed.

    This demonstrates how to process memories and respond to messages.
    Uses LLM service with user-managed message history.
    Memory response is optional - SMS channel provides it, Voice channel does not.
    """
    try:
        logger.info("-" * 80)
        logger.info(
            f"[CALLBACK] Message ready - Channel: {context.channel}, "
            f"Conv ID: {context.conversation_id[:8]}..."
        )
        logger.info(f"[CALLBACK] User message: {user_message}")

        global active_conversation_sid
        # Initialize conversation history with system message if needed
        conv_id = context.conversation_id
        active_conversation_sid = conv_id
        if conv_id not in conversation_messages:
            conversation_messages[conv_id] = []

        # Add current user message
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
        conversation_messages[conv_id].append(user_msg)

        # Retrieve memory only if Twilio Memory is enabled
        memory_response = None
        if taf.is_twilio_memory_enabled():
            try:
                memory_response = taf.retrieve_memory(context, query=user_message)
                logger.debug(f"Memory retrieved for conversation {conv_id}")
            except Exception as e:
                logger.error(
                    f"Failed to retrieve memory for conversation {conv_id}: {e}",
                    exc_info=True,
                )
        else:
            logger.debug(
                f"Twilio Memory not enabled, skipping memory retrieval for conversation {conv_id}"
            )

        # Log memory retrieval results
        if memory_response:
            obs_count = len(memory_response.observations) if memory_response.observations else 0
            sum_count = len(memory_response.summaries) if memory_response.summaries else 0
            logger.info(
                f"[MEMORY] Retrieved {obs_count} observations, {sum_count} summaries "
                f"for profile {context.profile_id}"
            )
        else:
            logger.info("[MEMORY] No memory response available for this channel")

        # Call LLM service with conversation history
        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            context=context,
            conversation_history=conversation_messages[conv_id],
        )

        # Send response through appropriate channel
        if llm_response:
            logger.info(f"[RESPONSE] Sending via {context.channel}: {llm_response[:100]}...")

            if context.channel == "voice":
                await voice_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )

            logger.info(f"[RESPONSE] Successfully sent via {context.channel}")
            logger.info("=" * 80)

            # Store assistant response in history
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": llm_response,
            }
            conversation_messages[conv_id].append(assistant_msg)
    except Exception as e:
        logger.error(f"[CALLBACK] Error handling message ready callback: {e}", exc_info=True)


taf.on_message_ready(handle_message_ready)


@app.post("/twiml")
async def post_twiml(From: str = Form(...)) -> Response:
    """Generate TwiML for Twilio voice calls."""
    logger.info("=" * 80)
    logger.info(f"[VOICE] Incoming call from: {From}")

    # Get WebSocket URL from environment
    public_domain = os.environ.get("VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"

    # Generate TwiML with conversation and participant setup
    # From contains the caller's phone number
    twiml = voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        called_phone_number="+18552759443",  # hardcoded Twilio number for demo
    )

    logger.info("[VOICE] TwiML generated, connecting to WebSocket")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    logger.info("[VOICE] WebSocket connection established")
    await voice_channel.handle_websocket(websocket)
    logger.info("[VOICE] WebSocket connection closed")
    logger.info("=" * 80)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
