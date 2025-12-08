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

import os
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import JSONResponse, Response
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from taf import TAF, TAFConfig
from taf.channels import SMSChannel
from taf.channels.voice import VoiceChannel
from taf.core.logging import get_logger, setup_logging
from taf.models.memory import MemoryRetrievalResponse
from taf.models.session import ConversationSession

load_dotenv()

# Configure structured logging using TAF's logging utilities
setup_logging(log_level="INFO", log_format="console")

logger = get_logger(__name__)

app = FastAPI(
    title="TAF Multi-Channel Demo",
    description="Multi-channel demo using Twilio Agentic Framework",
    version="1.0.0",
)

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
voice_channel = VoiceChannel(taf)
sms_channel = SMSChannel(taf)

llm_service = LLMService(taf)

# User-managed conversation history
# Key: conversation_id, Value: list of messages
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}


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
    conv_id = context.conversation_id
    try:
        logger.info(
            "Message ready for processing",
            conversation_id=conv_id,
            profile_id=context.profile_id,
            channel=context.channel,
        )

        if conv_id not in conversation_messages:
            conversation_messages[conv_id] = []

        # Add current user message
        user_msg: ChatCompletionUserMessageParam = {"role": "user", "content": user_message}
        conversation_messages[conv_id].append(user_msg)

        # Retrieve memory only if Twilio Memory is enabled
        memory_response = None
        if taf.is_twilio_memory_enabled():
            try:
                memory_response = await taf.retrieve_memory(context, query=user_message)
                logger.debug(
                    "Memory retrieved",
                    conversation_id=conv_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to retrieve memory",
                    conversation_id=conv_id,
                    error=str(e),
                    exc_info=True,
                )
        else:
            logger.debug(
                "Twilio Memory not enabled, skipping memory retrieval",
                conversation_id=conv_id,
            )

        # Log memory retrieval results
        if memory_response:
            obs_count = len(memory_response.observations) if memory_response.observations else 0
            sum_count = len(memory_response.summaries) if memory_response.summaries else 0
            logger.info(
                "Memory retrieved",
                conversation_id=conv_id,
                profile_id=context.profile_id,
                observations_count=obs_count,
                summaries_count=sum_count,
            )
        else:
            logger.info(
                "No memory response available",
                conversation_id=conv_id,
                channel=context.channel,
            )

        # Get the active websocket for this conversation if it's a voice channel
        active_websocket = (
            voice_channel.get_websocket(conv_id) if context.channel == "voice" else None
        )

        # Call LLM service with conversation history
        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            context=context,
            websocket=active_websocket,
            conversation_history=conversation_messages[conv_id],
        )

        # Send response through appropriate channel
        if llm_response:
            logger.info(
                "Sending response",
                conversation_id=conv_id,
                channel=context.channel,
            )

            if context.channel == "voice":
                await voice_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )
            elif context.channel == "sms":
                await sms_channel.send_response(
                    context.conversation_id, llm_response, role="assistant"
                )
            else:
                logger.error(
                    "Unknown channel, cannot send response",
                    conversation_id=conv_id,
                    channel=context.channel,
                )

            logger.info(
                "Successfully sent response",
                conversation_id=conv_id,
                channel=context.channel,
            )

            # Store assistant response in history
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": llm_response,
            }
            conversation_messages[conv_id].append(assistant_msg)
    except Exception as e:
        logger.error(
            "Error handling message ready callback",
            conversation_id=conv_id,
            error=str(e),
            exc_info=True,
        )


taf.on_message_ready(handle_message_ready)


@app.post("/sms")
async def sms_webhook(request: Request) -> JSONResponse:
    """Handle incoming SMS webhooks from Twilio."""
    try:
        form_data = await request.json()
        webhook_data = dict(form_data)

        # Process all events (including deduplicated communication.created)
        await sms_channel.process_webhook(webhook_data)
        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        logger.error("Error processing SMS webhook", error=str(e))
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


@app.post("/twiml")
async def post_twiml(
    from_number: str = Form(..., alias="From"),
    to_number: str = Form(..., alias="To"),
    call_sid: str = Form(..., alias="CallSid"),
) -> Response:
    """Generate TwiML for Twilio voice calls."""
    logger.info(
        "Incoming voice call",
        from_number=from_number,
        to_number=to_number,
        call_sid=call_sid,
    )

    # Get WebSocket URL from environment
    public_domain = os.environ.get("TWILIO_TAF_VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"
    callback_url = f"https://{public_domain}/conversation-relay-callback"

    # Generate TwiML with conversation and participant setup
    # From contains the caller's phone number, To contains the Twilio number
    twiml = await voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        to_number=to_number,
        from_number=from_number,
        call_sid=call_sid,
        action_url=callback_url,
    )

    logger.info("TwiML generated, connecting to WebSocket", call_sid=call_sid)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    logger.info("WebSocket connection established")
    await voice_channel.handle_websocket(websocket)
    logger.info("WebSocket connection closed")


@app.post("/conversation-relay-callback")
async def conversation_relay_callback(request: Request) -> Response:
    """Handle ConversationRelay callback webhook from Twilio."""
    return await voice_channel.handle_conversation_relay_callback(request)


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
