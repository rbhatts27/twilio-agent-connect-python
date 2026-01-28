"""
Anchor 1 Demo: Concurrent Cross-Channel Communication
All My Sons Moving & Storage - The Ramirez Family Quote Request

This demo showcases TAC's ability to handle concurrent voice and SMS channels
within a single conversation. Key scenarios demonstrated:

1. Customer calls for moving quote (voice primary)
2. AI asks for furniture photos
3. Customer texts photos while on call (SMS secondary)
4. AI acknowledges SMS, analyzes photos, responds on both channels
5. AI sends detailed quote breakdown via SMS while discussing on voice

Architecture:
- Single Maestro conversation ID links voice and SMS
- Profile ID enables cross-channel context
- Event-driven: SMS messages trigger processing within voice conversation
- Dashboard visualizes concurrent channel activity
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Optional

import uvicorn
from dashboard.event_handler import get_event_queue, setup_dashboard_logging
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from llm_service import LLMService
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from tac import TAC, TACConfig
from tac.channels import SMSChannel
from tac.channels.voice import VoiceChannel
from tac.core.logging import get_logger, setup_logging
from tac.models.memory import MemoryRetrievalResponse
from tac.models.session import ConversationSession

# Load environment from parent examples directory
load_dotenv(Path(__file__).parent.parent / ".env")

# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent

# Configure structured logging
setup_logging(log_level="INFO", log_format="console")
logger = get_logger(__name__)

app = FastAPI(
    title="Anchor 1: All My Sons Concurrent Channels Demo",
    description="Concurrent cross-channel communication for moving quotes",
    version="1.0.0",
)

# Initialize TAC
tac = TAC(config=TACConfig.from_env())

# Setup dashboard logging AFTER TAC initialization
setup_dashboard_logging()

# Initialize channels
voice_channel = VoiceChannel(tac)
sms_channel = SMSChannel(tac)

# Initialize LLM service
llm_service = LLMService(tac)

# =============================================================================
# Conversation State Management
# =============================================================================

# Conversation history keyed by conversation_id
conversation_messages: dict[str, list[ChatCompletionMessageParam]] = {}

# Track which conversations have active voice calls
# Key: conversation_id, Value: True if voice call is active
active_voice_calls: dict[str, bool] = {}

# Map phone numbers to conversation IDs for cross-channel linking
# Key: phone_number (E.164), Value: conversation_id
phone_to_conversation: dict[str, str] = {}


def link_phone_to_conversation(phone: str, conversation_id: str) -> None:
    """Link a phone number to a conversation for cross-channel routing."""
    phone_to_conversation[phone] = conversation_id
    logger.info(
        f"CROSS-CHANNEL | Linked {phone} to conversation {conversation_id[:20]}...",
        conversation_id=conversation_id,
    )


def get_conversation_for_phone(phone: str) -> Optional[str]:
    """Get the active conversation ID for a phone number."""
    return phone_to_conversation.get(phone)


# =============================================================================
# Message Handler (Unified for both channels)
# =============================================================================


async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
    incoming_channel: str = None,
) -> None:
    """
    Unified callback for processing messages from any channel.

    This demonstrates Anchor 1's concurrent channel handling:
    - Messages from voice and SMS both flow through here
    - Context is maintained across channels via profile_id
    - Responses go to the originating channel
    - Cross-channel awareness in AI instructions

    Args:
        user_message: The user's message
        context: ConversationSession with conversation details
        memory_response: Memory response from TAC (optional)
        incoming_channel: Override channel (for cross-channel messages)
    """
    conv_id = context.conversation_id
    channel = incoming_channel or context.channel

    try:
        # Initialize conversation history if needed
        if conv_id not in conversation_messages:
            conversation_messages[conv_id] = []

        # Add current user message with channel annotation
        user_msg: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"[{channel.upper()}] {user_message}",
        }
        conversation_messages[conv_id].append(user_msg)

        # Log incoming message
        logger.info(
            f"\n{'=' * 80}\n"
            f"{'VOICE' if channel == 'voice' else 'SMS'} MESSAGE | "
            f"{user_message[:50]}{'...' if len(user_message) > 50 else ''}",
            conversation_id=conv_id,
            channel=channel,
            profile_id=context.profile_id,
        )

        # Log memory retrieval
        if memory_response:
            memory_items = []
            if memory_response.observations:
                memory_items.append(f"{len(memory_response.observations)} observations")
            if memory_response.summaries:
                memory_items.append(f"{len(memory_response.summaries)} summaries")
            memory_summary = ", ".join(memory_items) if memory_items else "context"
            logger.info(
                f"MEMORY | Retrieved {memory_summary}",
                conversation_id=conv_id,
                channel=channel,
            )

        # Check for concurrent channel activity
        is_concurrent = (
            channel == "sms" and conv_id in active_voice_calls and active_voice_calls[conv_id]
        )

        if is_concurrent:
            logger.info(
                "CONCURRENT | SMS received during active voice call - cross-channel mode",
                conversation_id=conv_id,
            )

        # Get websocket for voice responses
        active_websocket = (
            voice_channel.get_websocket(conv_id) if context.channel == "voice" else None
        )

        # Process message with LLM
        logger.info(
            "AI AGENT | Processing message...",
            conversation_id=conv_id,
            channel=channel,
        )

        llm_response = await llm_service.process_message(
            user_message=user_message,
            memory_response=memory_response,
            context=context,
            websocket=active_websocket,
            conversation_history=conversation_messages[conv_id],
            incoming_channel=channel,
        )

        # Send response through appropriate channel
        if llm_response:
            if channel == "voice":
                await voice_channel.send_response(conv_id, llm_response, role="assistant")
            elif channel == "sms":
                await sms_channel.send_response(conv_id, llm_response, role="assistant")

            # Log response preview
            response_preview = (
                llm_response[:100] + "..." if len(llm_response) > 100 else llm_response
            )
            logger.info(
                f"AI RESPONSE [{channel.upper()}] | {response_preview}",
                conversation_id=conv_id,
                channel=channel,
            )

            # Store assistant response
            assistant_msg: ChatCompletionAssistantMessageParam = {
                "role": "assistant",
                "content": f"[{channel.upper()}] {llm_response}",
            }
            conversation_messages[conv_id].append(assistant_msg)

    except Exception as e:
        logger.error(
            "Error processing message",
            conversation_id=conv_id,
            channel=channel,
            error=str(e),
            exc_info=True,
        )


# Register the message callback with TAC
tac.on_message_ready(handle_message_ready)


# =============================================================================
# SMS Webhook Endpoints
# =============================================================================


@app.post("/webhook")
async def webhook_handler(request: Request) -> JSONResponse:
    """
    Handle incoming SMS webhooks from Twilio.

    This endpoint processes SMS messages that may be part of an ongoing
    voice conversation (concurrent channel scenario) or standalone SMS.
    """
    try:
        form_data = await request.json()
        webhook_data = dict(form_data)

        # Extract idempotency token for deduplication
        idempotency_token = request.headers.get("i-twilio-idempotency-token")

        # Check if this SMS is from a phone with an active voice conversation
        # This enables the concurrent channel behavior
        from_number = webhook_data.get("From") or webhook_data.get("from_address")
        event_type = webhook_data.get("EventType")

        if event_type == "onMessageAdded" and from_number:
            existing_conv = get_conversation_for_phone(from_number)
            if existing_conv and existing_conv in active_voice_calls:
                logger.info(
                    f"CONCURRENT SMS | Message from {from_number} linked to active voice call",
                    conversation_id=existing_conv,
                )
                # The webhook will still be processed by sms_channel, but with
                # the existing conversation context

        # Fire and forget - process webhook asynchronously
        asyncio.create_task(sms_channel.process_webhook(webhook_data, idempotency_token))

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        logger.error("SMS webhook error", error=str(e), exc_info=True)
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)


# =============================================================================
# Voice Endpoints
# =============================================================================


@app.post("/twiml")
async def post_twiml(
    from_number: str = Form(..., alias="From"),
    to_number: str = Form(..., alias="To"),
    call_sid: str = Form(..., alias="CallSid"),
) -> Response:
    """
    Generate TwiML for incoming voice calls.

    This sets up the voice channel and links the caller's phone number
    to the conversation for cross-channel SMS routing.
    """
    logger.info(
        f"\n{'=' * 80}\nINCOMING CALL | {from_number} -> {to_number}",
        call_sid=call_sid,
    )

    # Get WebSocket URL from environment
    public_domain = os.environ.get("TWILIO_TAC_VOICE_PUBLIC_DOMAIN", "")
    websocket_url = f"wss://{public_domain}/ws"
    callback_url = f"https://{public_domain}/conversation-relay-callback"

    # Generate TwiML with conversation and participant setup
    twiml = await voice_channel.handle_incoming_call(
        websocket_url=websocket_url,
        to_number=to_number,
        from_number=from_number,
        call_sid=call_sid,
        action_url=callback_url,
    )

    # Extract conversation ID from TwiML to link phone number
    # The conversation ID is in the TwiML as a parameter
    conv_match = re.search(r'name="conversationId" value="([^"]+)"', twiml)
    if conv_match:
        conversation_id = conv_match.group(1)
        # Link phone number to conversation for cross-channel routing
        link_phone_to_conversation(from_number, conversation_id)
        # Mark voice call as active
        active_voice_calls[conversation_id] = True
        logger.info(
            f"VOICE ACTIVE | Cross-channel enabled for {from_number}",
            conversation_id=conversation_id,
        )

    logger.info("CALL SETUP | TwiML generated, WebSocket connecting...", call_sid=call_sid)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Handle voice streaming WebSocket connection.

    When connected, marks the conversation as having an active voice call
    for concurrent channel detection.
    """
    logger.info("WEBSOCKET | Connected - voice streaming ready")

    # Handle the WebSocket connection
    await voice_channel.handle_websocket(websocket)

    logger.info("WEBSOCKET | Disconnected")


@app.post("/conversation-relay-callback")
async def conversation_relay_callback(request: Request) -> Response:
    """Handle ConversationRelay callback webhook from Twilio.

    Also cleans up active voice call tracking for cross-channel detection.
    """
    # Let the voice channel handle the callback
    response = await voice_channel.handle_conversation_relay_callback(request)

    # Clean up any stale active voice calls
    # (The voice channel closes conversations on call completion)
    for conv_id in list(active_voice_calls.keys()):
        # Check if the conversation is still in voice channel's active conversations
        if conv_id not in voice_channel._conversations:
            if active_voice_calls.get(conv_id):
                active_voice_calls[conv_id] = False
                logger.info(
                    "VOICE ENDED | Cross-channel disabled",
                    conversation_id=conv_id,
                )

    return response


# =============================================================================
# Dashboard Routes
# =============================================================================

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "dashboard" / "static")), name="static")


@app.get("/dashboard")
async def dashboard_page() -> FileResponse:
    """Serve the dashboard HTML page."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html", media_type="text/html"
    )


@app.get("/")
async def root() -> FileResponse:
    """Redirect root to dashboard."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html", media_type="text/html"
    )


@app.get("/events")
async def event_stream(request: Request) -> StreamingResponse:
    """SSE endpoint for streaming dashboard events."""

    async def event_generator():
        queue = get_event_queue()
        try:
            while True:
                if queue:
                    event = queue.popleft()
                    yield f"data: {event.model_dump_json()}\n\n"
                else:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            logger.info("Dashboard client disconnected")
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =============================================================================
# Health Check
# =============================================================================


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "demo": "Anchor 1 - Concurrent Cross-Channel",
            "company": "All My Sons Moving & Storage",
            "channels": ["voice", "sms"],
            "active_voice_calls": len([c for c, active in active_voice_calls.items() if active]),
        }
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Anchor 1 Demo: Concurrent Cross-Channel Communication")
    print("All My Sons Moving & Storage")
    print("=" * 60)
    print("\nEndpoints:")
    print("  Dashboard:    http://localhost:8000/dashboard")
    print("  SMS Webhook:  POST /webhook")
    print("  Voice TwiML:  POST /twiml")
    print("  Voice WS:     WS /ws")
    print("  Health:       GET /health")
    print("\nScenario: The Ramirez Family Quote Request")
    print("  1. Maria calls for a moving quote (voice)")
    print("  2. AI asks for furniture photos")
    print("  3. Maria texts photos while on call (SMS)")
    print("  4. AI analyzes photos and responds on both channels")
    print("  5. AI sends quote breakdown via SMS")
    print("=" * 60 + "\n")

    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(levelprefix)s %(message)s"
    uvicorn_log_config["formatters"]["access"]["fmt"] = (
        '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s'
    )

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        log_level="warning",
        access_log=False,
        log_config=uvicorn_log_config,
    )
