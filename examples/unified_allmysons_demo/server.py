"""
Unified All My Sons Demo Server

Single server running on port 8000 that supports all 6 anchor scenarios.
The dashboard provides a dropdown to select which anchor demo to run.
Switching anchors changes the AI agent behavior without restarting the server.

Architecture:
- Single FastAPI app handles SMS + Voice + Dashboard
- Active anchor is selected via API and controls message handling
- Dashboard streams events via SSE with enhanced SMS content display
"""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Optional

import uvicorn
from anchors import ANCHOR_REGISTRY
from anchors.base import BaseAnchor
from dashboard.event_handler import (
    get_event_queue,
    push_anchor_event,
    push_sms_event,
    setup_dashboard_logging,
)
from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

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
    title="Unified All My Sons Demo Server",
    description="Single server for all anchor scenarios with dashboard selection",
    version="1.0.0",
)

# Initialize TAC
tac = TAC(config=TACConfig.from_env())

# Setup dashboard logging AFTER TAC initialization
setup_dashboard_logging()

# Initialize channels
voice_channel = VoiceChannel(tac)
sms_channel = SMSChannel(tac)

# =============================================================================
# Anchor Management
# =============================================================================

# Active anchor instance (default: anchor1)
active_anchor: Optional[BaseAnchor] = None


def get_active_anchor() -> BaseAnchor:
    """Get the currently active anchor, initializing anchor1 if needed."""
    global active_anchor
    if active_anchor is None:
        select_anchor("anchor1")
    return active_anchor  # type: ignore[return-value]


def select_anchor(anchor_id: str) -> BaseAnchor:
    """Select and initialize an anchor by ID."""
    global active_anchor

    if anchor_id not in ANCHOR_REGISTRY:
        raise ValueError(f"Unknown anchor: {anchor_id}. Available: {list(ANCHOR_REGISTRY.keys())}")

    anchor_class = ANCHOR_REGISTRY[anchor_id]
    active_anchor = anchor_class(
        tac=tac,
        sms_channel=sms_channel,
        voice_channel=voice_channel,
    )

    logger.info(f"ANCHOR SELECTED | {active_anchor.name} ({anchor_id})")
    push_anchor_event(anchor_id, active_anchor.name)

    return active_anchor


# Initialize default anchor
select_anchor("anchor1")


# =============================================================================
# Message Handler (Delegates to active anchor)
# =============================================================================


async def handle_message_ready(
    user_message: str,
    context: ConversationSession,
    memory_response: Optional[MemoryRetrievalResponse],
    incoming_channel: str = None,
) -> None:
    """Unified callback that delegates to the active anchor's handler."""
    anchor = get_active_anchor()
    await anchor.handle_message(
        user_message=user_message,
        context=context,
        memory_response=memory_response,
        incoming_channel=incoming_channel,
    )


# Register the message callback with TAC
tac.on_message_ready(handle_message_ready)


# =============================================================================
# Anchor Selection API
# =============================================================================


@app.get("/api/anchors")
async def list_anchors() -> JSONResponse:
    """List all available anchor scenarios."""
    anchors = []
    for anchor_id, anchor_class in ANCHOR_REGISTRY.items():
        # Create a temporary instance to get scenario info
        temp = anchor_class(tac=tac, sms_channel=sms_channel, voice_channel=voice_channel)
        anchors.append(temp.get_scenario_info())
    return JSONResponse(content={"anchors": anchors})


@app.get("/api/active-anchor")
async def get_active_anchor_info() -> JSONResponse:
    """Get the currently active anchor."""
    anchor = get_active_anchor()
    return JSONResponse(content=anchor.get_scenario_info())


@app.post("/api/select-anchor")
async def select_anchor_endpoint(request: Request) -> JSONResponse:
    """Select a new active anchor scenario."""
    try:
        body = await request.json()
        anchor_id = body.get("anchor_id")

        if not anchor_id:
            return JSONResponse(
                content={"error": "anchor_id is required"}, status_code=400
            )

        anchor = select_anchor(anchor_id)
        return JSONResponse(content=anchor.get_scenario_info())

    except ValueError as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error("Error selecting anchor", error=str(e), exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)


# =============================================================================
# SMS Webhook Endpoints
# =============================================================================


@app.post("/webhook")
async def webhook_handler(request: Request) -> JSONResponse:
    """Handle incoming SMS webhooks from Twilio."""
    try:
        form_data = await request.json()
        webhook_data = dict(form_data)

        # Extract idempotency token for deduplication
        idempotency_token = request.headers.get("i-twilio-idempotency-token")

        # Extract SMS details for enhanced dashboard display
        event_type = webhook_data.get("EventType")
        from_number = webhook_data.get("From") or webhook_data.get("from_address")

        if event_type == "onMessageAdded":
            # Extract message body and media for dashboard
            message_body = webhook_data.get("Body", "")
            conversation_id = webhook_data.get("ConversationSid", "")

            # Extract media attachments if present
            num_media = int(webhook_data.get("NumMedia", 0))
            media_urls = []
            for i in range(num_media):
                media_url = webhook_data.get(f"MediaUrl{i}", "")
                media_type = webhook_data.get(f"MediaContentType{i}", "image/jpeg")
                if media_url:
                    media_urls.append({
                        "url": media_url,
                        "content_type": media_type,
                        "filename": f"attachment_{i + 1}",
                    })

            # Push enhanced SMS event to dashboard
            if message_body or media_urls:
                push_sms_event(
                    conversation_id=conversation_id,
                    from_number=from_number or "",
                    sms_body=message_body,
                    media_urls=media_urls if media_urls else None,
                    profile_id=webhook_data.get("profile_id")
                    or webhook_data.get("ProfileId"),
                )

            # Check cross-channel linking for active anchor
            anchor = get_active_anchor()
            if from_number:
                existing_conv = anchor.get_conversation_for_phone(from_number)
                if existing_conv and existing_conv in anchor.active_voice_calls:
                    logger.info(
                        f"CONCURRENT SMS | Message from {from_number} "
                        f"linked to active voice call",
                        conversation_id=existing_conv,
                    )

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
    """Generate TwiML for incoming voice calls."""
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
    conv_match = re.search(r'name="conversationId" value="([^"]+)"', twiml)
    if conv_match:
        conversation_id = conv_match.group(1)
        anchor = get_active_anchor()
        anchor.link_phone_to_conversation(from_number, conversation_id)
        anchor.active_voice_calls[conversation_id] = True
        logger.info(
            f"VOICE ACTIVE | Cross-channel enabled for {from_number}",
            conversation_id=conversation_id,
        )

    logger.info("CALL SETUP | TwiML generated, WebSocket connecting...", call_sid=call_sid)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Handle voice streaming WebSocket connection."""
    logger.info("WEBSOCKET | Connected - voice streaming ready")
    await voice_channel.handle_websocket(websocket)
    logger.info("WEBSOCKET | Disconnected")


@app.post("/conversation-relay-callback")
async def conversation_relay_callback(request: Request) -> Response:
    """Handle ConversationRelay callback webhook from Twilio."""
    response = await voice_channel.handle_conversation_relay_callback(request)

    # Clean up active voice calls
    anchor = get_active_anchor()
    for conv_id in list(anchor.active_voice_calls.keys()):
        if conv_id not in voice_channel._conversations:
            if anchor.active_voice_calls.get(conv_id):
                anchor.active_voice_calls[conv_id] = False
                logger.info(
                    "VOICE ENDED | Cross-channel disabled",
                    conversation_id=conv_id,
                )

    return response


# =============================================================================
# Dashboard Routes
# =============================================================================

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "dashboard" / "static")),
    name="static",
)


@app.get("/dashboard")
async def dashboard_page() -> FileResponse:
    """Serve the dashboard HTML page."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html",
        media_type="text/html",
    )


@app.get("/")
async def root() -> FileResponse:
    """Redirect root to dashboard."""
    return FileResponse(
        BASE_DIR / "dashboard" / "templates" / "dashboard.html",
        media_type="text/html",
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
    anchor = get_active_anchor()
    return JSONResponse({
        "status": "healthy",
        "demo": "Unified All My Sons Demo",
        "active_anchor": anchor.anchor_id,
        "active_anchor_name": anchor.name,
        "channels": ["voice", "sms"],
        "active_voice_calls": len(
            [c for c, active in anchor.active_voice_calls.items() if active]
        ),
    })


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Unified All My Sons Demo Server")
    print("All 6 Anchor Scenarios in One Place")
    print("=" * 60)
    print("\nEndpoints:")
    print("  Dashboard:       http://localhost:8000/dashboard")
    print("  SMS Webhook:     POST /webhook")
    print("  Voice TwiML:     POST /twiml")
    print("  Voice WS:        WS /ws")
    print("  Health:          GET /health")
    print("  List Anchors:    GET /api/anchors")
    print("  Active Anchor:   GET /api/active-anchor")
    print("  Select Anchor:   POST /api/select-anchor")
    print("\nAvailable Anchors:")
    for aid, aclass in ANCHOR_REGISTRY.items():
        temp = aclass(tac=tac, sms_channel=sms_channel, voice_channel=voice_channel)
        print(f"  {aid}: {temp.name} - {temp.short_description}")
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
